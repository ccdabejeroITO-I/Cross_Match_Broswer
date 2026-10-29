"""Sequential self-dedup then cross-match using the existing matching engine.

Stage 1 and Stage 2 have isolated workspaces and rule sets. Stage 2 is fed
only the Stage 1 VALIDATED records, with original File A headers preserved.
Final files contain one and only one outcome row per original File A record;
File B reference rows are only display rows, excluded from outcome counts.
"""
from __future__ import annotations

import csv
import io
import re
from contextlib import contextmanager
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

from engine import crossmatch_engine as engine
from services.excel_export import csv_zip_to_excel
from config import CPU_WORKERS, MEMORY_PERCENT

SHEETS = ('SUMMARY','VALIDATED RECORDS','DUPLICATE RECORDS','RECORDS FOR REVIEW')
EXTRA = ('DedupType','MatchPercentage','ConflictReason')


@contextmanager
def _open_csv(archive: zipfile.ZipFile, sheet: str):
    """Read all stage CSV continuation sheets as one logical data stream.

    The first sheet's header is used; continuation headers are verified and
    omitted. This prevents >1,048,576-row stages from silently disappearing.
    """
    names=[]
    for name in archive.namelist():
        match=re.fullmatch(re.escape(sheet)+r'(?: (\d+))?\.csv',name)
        if match:
            names.append((int(match.group(1) or 1),name))
    names.sort()
    if not names or names[0][0] != 1:
        raise ValueError(f'Sequential stage output missing {sheet}.csv.')
    def lines():
        first_header=None
        for part, name in names:
            with io.TextIOWrapper(archive.open(name),encoding='utf-8-sig',newline='') as f:
                header=next(csv.reader(f),None)
                if first_header is None:
                    first_header=header
                    if not first_header:
                        raise ValueError(f'Sequential stage result missing header: {name}.')
                    # The consumer's csv.reader expects one header line.
                    # Correctly quote arbitrary header names, including commas.
                    buf=io.StringIO(newline='')
                    csv.writer(buf).writerow(header)
                    yield buf.getvalue()
                elif header != first_header:
                    raise ValueError(f'Sequential continuation headers differ: {name}.')
                yield from f
    yield lines()


def _copy_rows(archive: zipfile.ZipFile, name: str, output, columns: list[str], *, reference: bool=True) -> int:
    with _open_csv(archive, name) as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f'Sequential stage output has no headers: {name}.')
        count=0
        for row in reader:
            if not reference and row.get('DedupType','') == 'REFERENCE (FILE B)':
                continue
            output.writerow([row.get(col,'') for col in columns])
            count+=1
    return count


def _write_section(writer, columns, label: str):
    """Visual heading row, not an outcome. Keep the public column schema intact."""
    writer.writerow([label] + [''] * (len(columns) - 1))


def _copy_grouped_stage(archive: zipfile.ZipFile, writer, columns: list[str], process: int):
    """Stream actual engine group identities in public reference-first order.

    Private per-stage metadata is deliberately NOT copied to the final public
    archive; only human-readable non-beneficiary heading rows are inserted.
    """
    section = ('SECTION 1 — PROCESS 1: SELF-DEDUPLICATION OF FILE A' if process == 1
               else 'SECTION 2 — PROCESS 2: FILE A vs FILE B CROSS-MATCHING')
    _write_section(writer, columns, section)
    group_member = '_INTERNAL_DUP_GROUPS.csv'
    with _open_csv(archive, 'DUPLICATE RECORDS') as data_file:
        reader = csv.DictReader(data_file)
        if list(reader.fieldnames or []) != columns:
            raise ValueError('Duplicate stage schema differs from original File A public columns.')
        meta = (io.TextIOWrapper(archive.open(group_member), encoding='utf-8', newline='')
                if group_member in archive.namelist() else None)
        count = 0; refs = 0; last_gid = None; number = 0
        try:
            group_reader = csv.reader(meta) if meta else iter(())
            for row in reader:
                try:
                    group_entry = next(group_reader)
                except StopIteration:
                    raise RuntimeError('Missing verified duplicate-group metadata in stage archive.')
                if len(group_entry) != 2:
                    raise RuntimeError('Malformed duplicate-group metadata.')
                gid = int(group_entry[0])
                if gid <= 0:
                    raise RuntimeError('Duplicate row has no verified internal group ID.')
                if gid != last_gid:
                    number += 1
                    _write_section(writer, columns,
                        f'GROUP {number} — FILE A SELF-DEDUP' if process == 1 else
                        f'GROUP {number} — FILE A vs FILE B CROSS-MATCH')
                    last_gid = gid
                # Source ordering was already guaranteed by GroupedDuplicateWriter.
                label = row.get('DedupType','')
                if process == 1 and label.startswith('REFERENCE'):
                    # Fail closed rather than hiding a wrongly exported Clean
                    # row or silently inflating beneficiary outcome totals.
                    raise RuntimeError('Process 1 contains an unexpected reference-only row.')
                writer.writerow([row.get(col,'') for col in columns])
                count += 1
            if meta and next(group_reader, None) is not None:
                raise RuntimeError('Duplicate-group metadata has more rows than the result.')
        finally:
            if meta: meta.close()
    if not count:
        _write_section(writer, columns, 'No matching records in this section.')
    return count, refs


def _copy_review_stage(archive: zipfile.ZipFile, writer, columns: list[str], process: int):
    label = ('SECTION 1 — PROCESS 1: FILE A REVIEW' if process == 1 else
             'SECTION 2 — PROCESS 2: CROSS-MATCH REVIEW')
    _write_section(writer, columns, label)
    count = _copy_rows(archive, 'RECORDS FOR REVIEW', writer, columns, reference=False)
    if not count:
        _write_section(writer, columns, 'No matching records in this section.')
    return count


def _count_records(file_b: str, sheet_b: str) -> int:
    plan=engine.inspect_input(file_b,sheet_b)
    return sum(len(chunk) for chunk in engine.iter_input_chunks(plan, 50000))


def run_sequential(request: dict, log: Callable[[str],None]):
    base=Path(request['output_folder'])
    base.mkdir(parents=True,exist_ok=True)
    # Pipeline intermediates are deleted after verification; finals remain in exports.
    with tempfile.TemporaryDirectory(prefix='sequential_',dir=str(base)) as temporary:
        working=Path(temporary)
        original_headers=engine.inspect_input(request['file_a'],request['sheet_a']).headers
        if len(original_headers) != len(set(original_headers)):
            raise ValueError('Sequential mode needs unique original File A header names.')
        reserved=set(EXTRA)
        if reserved.intersection(original_headers):
            raise ValueError('Sequential input already contains an output metadata column (DedupType/MatchPercentage/ConflictReason). Rename that source header to avoid losing original values.')
        shared=dict(
            exhaustive=False,  # Both sequential stages use indexed discovery.
            group_sidecar=True,
            fuzzy=request['fuzzy'],enable_swap=request['swap'],
            fuzzy_threshold=request['fuzzy_threshold'],min_age=request['min_age'],max_age=request['max_age'],
            cpu_workers=CPU_WORKERS, memory_limit_percent=MEMORY_PERCENT,
            fuzzy_block_limit=0,fuzzy_max_candidates=-1,fuzzy_birth_year_window=-1,
            export_format='csv_zip',
        )
        # Exact same matcher and original File A schema used for both stages.
        log('Sequential Process 1: Within File A self-deduplication. Keep One TRUE_DUPLICATE: '
            + ('ON' if bool(request.get('keep_one_true_duplicate', True)) else 'OFF')
            + '. Process 2 Keep One: NOT APPLICABLE.')
        opts1=engine.ScaleOptions(mode=engine.MODE_FILE_A,
            keep_one_true_duplicate=bool(request.get('keep_one_true_duplicate',True)),
            output_folder=str(working/'process1'),output_file=str(working/'process1'/'Process_1.zip'),
            source_a_label=request['source_a_name'],advanced_conditions=request.get('advanced_conditions'),**shared)
        stage1=engine.run_engine(request['file_a'],None,request['sheet_a'],None,request['mapping_a_path'],None,opts1,log)
        zip1=Path(stage1['paths']['csv_zip'])
        stage1_counts=stage1['counts']
        stage1_clean=int(stage1_counts['Validated Records'])
        clean_csv=working/'Process1_Clean_File_A.csv'
        with zipfile.ZipFile(zip1) as z1, clean_csv.open('w',encoding='utf-8-sig',newline='') as outfile:
            writer=csv.writer(outfile);writer.writerow(original_headers)
            # These exported CSV values may be escaped to protect against Excel
            # formulas. Undo only the output-only apostrophe before rematching;
            # the final export will escape dangerous raw values again.
            with _open_csv(z1,'VALIDATED RECORDS') as read_clean:
                reader=csv.DictReader(read_clean)
                clean_rows=0
                for row in reader:
                    originals=[]
                    for field in original_headers:
                        value=row.get(field,'')
                        if value.startswith("'") and value[1:].lstrip().startswith(('=','+','-','@')):
                            value=value[1:]
                        originals.append(value)
                    writer.writerow(originals)
                    clean_rows+=1
        if clean_rows!=stage1_clean:
            raise RuntimeError(f'Process 1 clean count failed: {clean_rows} vs {stage1_clean}.')
        stage2=None
        if stage1_clean:
            log(f'Sequential Process 2: Cross Match {stage1_clean:,} eligible Clean File A rows against File B.')
            opts2=engine.ScaleOptions(mode=engine.MODE_CROSS,
                keep_one_true_duplicate=False,
                output_folder=str(working/'process2'),output_file=str(working/'process2'/'Process_2.zip'),
                source_a_label=request['source_a_name'],source_b_label=request['source_b_name'],
                advanced_conditions=request.get('advanced_conditions_cross'),**shared)
            stage2=engine.run_engine(str(clean_csv),request['file_b'],'CSV',request['sheet_b'],request['mapping_a_path'],request['mapping_b_path'],opts2,log)
            second=stage2['counts']
            if sum(int(second[k]) for k in ('Validated Records','Duplicate Records','Records for Review'))!=stage1_clean:
                raise RuntimeError('Process 2 did not classify each Process 1 clean record exactly once.')
        else:
            log('Sequential Process 2: skipped matching (no eligible Process 1 Clean records).')

        a_rows=int(stage1_counts['File A Rows'])
        b_rows=int(stage2['counts']['File B Rows']) if stage2 else _count_records(request['file_b'],request['sheet_b'])
        valid=int(stage2['counts']['Validated Records']) if stage2 else 0
        duplicate=int(stage1_counts['Duplicate Records'])+(int(stage2['counts']['Duplicate Records']) if stage2 else 0)
        review=int(stage1_counts['Records for Review'])+(int(stage2['counts']['Records for Review']) if stage2 else 0)
        if valid+duplicate+review!=a_rows:
            raise RuntimeError(f'Sequential File A integrity failure: {a_rows} vs {valid}+{duplicate}+{review}.')
        b_refs=0
        if stage2:
            with zipfile.ZipFile(stage2['paths']['csv_zip']) as z2, _open_csv(z2,'DUPLICATE RECORDS') as f:
                b_refs=sum(row.get('DedupType')=='REFERENCE (FILE B)' for row in csv.DictReader(f))
        # Process 1 is classification-only: no retained Clean reference
        # records are re-exported in its Duplicate worksheet.
        log('Sequential stage counts: Process 1='+repr(stage1_counts)+'; Process 2='+repr(stage2['counts'] if stage2 else None))
        full_headers=list(original_headers)
        if stage2:
            with zipfile.ZipFile(stage2['paths']['csv_zip']) as z2, _open_csv(z2,'DUPLICATE RECORDS') as input_file:
                second_headers=next(csv.reader(input_file),[])
            # Strict desktop public schema: no additional File B-only headings.
            # File B references must be projected into the original File A layout.
            if second_headers != list(original_headers) + list(EXTRA):
                raise ValueError('Process 2 public headers must equal File A originals plus result fields.')
        full_headers += list(EXTRA)
        log('Sequential Process 3: streaming combined, non-overlapping results.')
        final_zip=base/'CrossMatch_Sequential_Results.zip'
        partial=final_zip.with_name(final_zip.stem+'.partial.zip')
        import contextlib
        with contextlib.ExitStack() as stack:
            z1=stack.enter_context(zipfile.ZipFile(zip1))
            z2=stack.enter_context(zipfile.ZipFile(stage2['paths']['csv_zip'])) if stage2 else None
            with tempfile.TemporaryDirectory(prefix='seq_output_',dir=str(base)) as sheetdir:
                sheetfiles=[]
                for sheet in SHEETS:
                    p=Path(sheetdir)/(sheet+'.csv');sheetfiles.append((sheet,p))
                    with p.open('w',encoding='utf-8-sig',newline='') as output:
                        writer=csv.writer(output)
                        if sheet=='SUMMARY':
                            from services.desktop_export_style import SUMMARY_COLUMNS
                            writer.writerow(SUMMARY_COLUMNS)
                            stage2_counts=stage2['counts'] if stage2 else {
                                'Validated Records':0,'Duplicate Records':0,'Records for Review':0}
                            # Preserve both stage-level totals and the original
                            # File A final invariant, following desktop v6.33.
                            writer.writerow(('PROCESS 1 — WITHIN FILE A',a_rows,
                                stage1_counts['Validated Records'],stage1_counts['Duplicate Records'],
                                stage1_counts['Records for Review']))
                            writer.writerow(('PROCESS 2 — FILE A vs FILE B',stage1_clean,
                                stage2_counts['Validated Records'],stage2_counts['Duplicate Records'],
                                stage2_counts['Records for Review']))
                            writer.writerow(('OVERALL FINAL RESULT',a_rows,valid,duplicate,review))
                            continue
                        writer.writerow(full_headers)
                        tally=0
                        if sheet=='VALIDATED RECORDS':
                            if z2:tally+=_copy_rows(z2,sheet,writer,full_headers,reference=False)
                        elif sheet=='DUPLICATE RECORDS':
                            emitted, _=_copy_grouped_stage(z1,writer,full_headers,1)
                            if emitted != int(stage1_counts['Duplicate Records']):
                                raise RuntimeError('Process 1 duplicate export must include only classified duplicate rows.')
                            tally+=emitted
                            if z2:
                                emitted, _=_copy_grouped_stage(z2,writer,full_headers,2)
                                tally+=emitted
                            else:
                                _write_section(writer,full_headers,'SECTION 2 — PROCESS 2: FILE A vs FILE B CROSS-MATCHING')
                                _write_section(writer,full_headers,'No matching records in this section.')
                        else:
                            tally+=_copy_review_stage(z1,writer,full_headers,1)
                            if z2:tally+=_copy_review_stage(z2,writer,full_headers,2)
                            else:
                                _write_section(writer,full_headers,'SECTION 2 — PROCESS 2: CROSS-MATCH REVIEW')
                                _write_section(writer,full_headers,'No matching records in this section.')
                        expected={'VALIDATED RECORDS':valid,'DUPLICATE RECORDS':duplicate+b_refs,'RECORDS FOR REVIEW':review}[sheet]
                        if tally!=expected:
                            raise RuntimeError(f'Sequential {sheet} export count failed: {tally} vs {expected}.')
                with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as zout:
                    for sheet,p in sheetfiles:zout.write(p,sheet+'.csv')
        with zipfile.ZipFile(partial) as check:
            if check.testzip() is not None or len(check.namelist())!=4:raise RuntimeError('Final sequential result archive failed integrity check.')
        partial.replace(final_zip)
        paths={'csv_zip':str(final_zip)}
        if request.get('export_format')=='xlsx':
            xlsx=base/'CrossMatch_Sequential_Results.xlsx'
            csv_zip_to_excel(final_zip,xlsx)
            paths['workbook']=str(xlsx)
        counts={'File A Rows':a_rows,'File B Rows':b_rows,'Validated Records':valid,'Duplicate Records':duplicate,
                'Records for Review':review,'File B Reference Rows in Duplicate Sheet':b_refs,
                'Process 1 Retained Reference Display Rows':0,
                'Duplicate Sheet Rows':duplicate+b_refs}
        log(f'Sequential completed: A={a_rows:,}; Clean={valid:,}; Duplicate={duplicate:,}; Review={review:,}.')
        return {'paths':paths,'counts':counts,'integrity_check':True,'export_integrity_check':True,
                'reference_only_audit':{'classification_scope':'File A only','file_a_rows':a_rows,
                    'validated':valid,'duplicate':duplicate,'review':review,
                    'file_b_reference_rows':b_rows,'file_b_classified_rows':0,
                    'file_b_reference_display_rows':b_refs},
                'export_format':request.get('export_format','xlsx'), 'sequential':{
                    'process_1':stage1_counts,'process_2':stage2['counts'] if stage2 else None,
                    'process_2_skipped':not bool(stage2),'file_a_count_verified':True},
                'no_loss_output':True}
