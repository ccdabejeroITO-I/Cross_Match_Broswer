"""Stream the Web engine's CSV ZIP results into the desktop-style Excel workbook.

Uses the SAME v6.33-derived XlsxWriter formats and public-sheet schema as
crossmatch_engine.export_results(). This renderer is required for Sequential
mode, whose stage outputs are consolidated as CSV before downloading Excel.
No matching or classification changes take place here.
"""
from __future__ import annotations

import csv
import io
import os
import threading
import uuid
import zipfile
from pathlib import Path

import xlsxwriter
from services.desktop_export_style import (
    CLASS_PALETTE, HEADER_STYLE, OVERALL_FILL, PUBLIC_FIELDS,
    REVIEW_FILL, SUMMARY_COLUMNS, VALIDATED_FILL, make_group_formats,
)

EXCEL_MAX_ROWS = 1_048_576
EXCEL_MAX_COLUMNS = 16_384
EXCEL_MAX_CELL_LENGTH = 32_767
_excel_conversion_lock = threading.Lock()
PRIMARY_SHEETS = ('SUMMARY', 'VALIDATED RECORDS', 'DUPLICATE RECORDS', 'RECORDS FOR REVIEW')


def _unique_sheet_name(base: str, used: set[str]) -> str:
    base = str(base).strip().strip("'") or 'RESULTS'
    base = ''.join('_' if ch in '[]:*?/\\' else ch for ch in base)[:31]
    name, suffix = base, 2
    while name.casefold() in used:
        tail = f' {suffix}'
        name = base[:31-len(tail)] + tail
        suffix += 1
    used.add(name.casefold())
    return name


def _group_first(row: list[str], marker_col: int, reason_col: int, ordinal: int) -> bool:
    if ordinal == 0:
        return True
    kind = row[marker_col].upper().strip() if marker_col >= 0 and marker_col < len(row) else ''
    reason = row[reason_col].strip().casefold() if reason_col >= 0 and reason_col < len(row) else ''
    return kind.startswith('REFERENCE (FILE B)') or reason.startswith('reference record | file a')


def _cell_width(header: str) -> int:
    if header == 'ConflictReason':
        return 70
    if header in ('DedupType', 'MatchPercentage'):
        return 22
    return max(10, min(45, len(header) + 3))


def _checked_text(value: str, stem: str) -> str:
    if len(value) > EXCEL_MAX_CELL_LENGTH:
        raise ValueError(f'{stem}: Excel cell exceeds 32,767 characters. CSV ZIP is still available.')
    return value


def csv_zip_to_excel(zip_path: Path, output_path: Path) -> Path:
    """Produce atomic, desktop-style, memory-bounded XLSX from classified CSV ZIP.

    Input CSV exports must retain the original File A column order and append
    only DedupType, MatchPercentage and ConflictReason. Reference-only File B
    rows remain supporting group rows and are never counted by this renderer.
    """
    zip_path, output_path = Path(zip_path).resolve(), Path(output_path).resolve()
    if not zip_path.is_file():
        raise FileNotFoundError('CSV ZIP results are no longer available.')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with _excel_conversion_lock:
        if output_path.is_file() and output_path.stat().st_mtime_ns >= zip_path.stat().st_mtime_ns:
            return output_path
        temporary = output_path.with_name(f'{output_path.stem}.{uuid.uuid4().hex}.partial.xlsx')
        try:
            with zipfile.ZipFile(zip_path) as archive:
                members = {Path(item.filename).stem.upper(): item for item in archive.infolist()
                           if not item.is_dir() and item.filename.lower().endswith('.csv')}
                if not all(name in members for name in PRIMARY_SHEETS):
                    missing = [name for name in PRIMARY_SHEETS if name not in members]
                    raise ValueError(f'Results archive is missing required sheets: {missing}')
                with xlsxwriter.Workbook(str(temporary), {
                    'constant_memory': True, 'use_zip64': True,
                    'strings_to_formulas': False, 'strings_to_urls': False,
                    'strings_to_numbers': False,
                    'tmpdir': str(output_path.parent),
                }) as workbook:
                    header_fmt = workbook.add_format(HEADER_STYLE)
                    validated_fmt = workbook.add_format({'bg_color': VALIDATED_FILL, 'valign': 'top'})
                    review_fmt = workbook.add_format({'bg_color': REVIEW_FILL, 'valign': 'top', 'text_wrap': True})
                    regular_summary_fmt = workbook.add_format({'num_format': '#,##0', 'valign': 'vcenter'})
                    overall_summary_fmt = workbook.add_format({'num_format': '#,##0', 'valign': 'vcenter',
                                                                'bold': True, 'bg_color': OVERALL_FILL})
                    row_styles, classification_styles = make_group_formats(workbook)
                    section_heading_fmt = workbook.add_format({
                        'bg_color': '#305496', 'font_color': '#FFFFFF', 'bold': True,
                        'valign': 'vcenter', 'text_wrap': True, 'border': 1, 'border_color': '#8EA9C1'})
                    group_heading_fmt = workbook.add_format({
                        'bg_color': '#DCE9F5', 'font_color': '#17365D', 'bold': True,
                        'valign': 'vcenter', 'border': 1, 'border_color': '#8EA9C1'})
                    empty_heading_fmt = workbook.add_format({
                        'bg_color': '#F2F4F8', 'font_color': '#5A6471', 'italic': True})
                    used_names: set[str] = set()
                    # Maintain group ordinal across continuation parts, with
                    # explicit reference row and source-row reason boundaries.
                    group_ordinal = 0
                    for sheet_name in PRIMARY_SHEETS:
                        member = members[sheet_name]
                        with archive.open(member) as raw, io.TextIOWrapper(raw, encoding='utf-8-sig', newline='') as txt:
                            reader = csv.reader(txt)
                            header = next(reader, None)
                            if header is None:
                                raise ValueError(f'{sheet_name}: result sheet has no header.')
                            if len(header) > EXCEL_MAX_COLUMNS:
                                raise ValueError(f'{sheet_name}: too many columns for Excel.')
                            summary = sheet_name == 'SUMMARY'
                            duplicate = sheet_name == 'DUPLICATE RECORDS'
                            if summary and tuple(header) != SUMMARY_COLUMNS:
                                raise ValueError(f'Summary schema differs from desktop v6.33: {header}')
                            if not summary and tuple(header[-3:]) != PUBLIC_FIELDS:
                                raise ValueError(f'{sheet_name}: missing approved result columns.')
                            dtype_idx = header.index('DedupType') if duplicate else -1
                            reason_idx = header.index('ConflictReason') if duplicate else -1
                            part, ws, row_index = 0, None, 0
                            active_section = ''
                            active_group = ''
                            explicit_group = False
                            first_in_group = False
                            group_ordinal = 0  # restart in Process 2
                            def next_sheet():
                                nonlocal ws, row_index, part
                                part += 1
                                name = sheet_name if part == 1 else f'{sheet_name[:26]} {part}'
                                ws = workbook.add_worksheet(_unique_sheet_name(name, used_names))
                                ws.hide_gridlines(2)
                                ws.freeze_panes(1, 0)
                                ws.set_row(0, 28)
                                for col, title in enumerate(header):
                                    ws.set_column(col, col, 38 if summary and col == 0 else
                                                  25 if summary else _cell_width(title))
                                    ws.write_string(0, col, _checked_text(title, sheet_name), header_fmt)
                                if not summary and not duplicate:
                                    # Avoid a million-row automatic filter in grouped duplicates.
                                    pass
                                row_index = 1
                            def put_heading(label: str, kind: str):
                                nonlocal row_index, group_ordinal, first_in_group, explicit_group
                                if row_index >= EXCEL_MAX_ROWS:
                                    next_sheet()
                                fmt = (section_heading_fmt if kind == 'section' else
                                       group_heading_fmt if kind == 'group' else empty_heading_fmt)
                                # Merge only the current row, which works with
                                # XlsxWriter constant_memory and leaves table
                                # columns unchanged. Do not truncate headings.
                                if len(header) > 1:
                                    ws.merge_range(row_index, 0, row_index, len(header)-1,
                                                   _checked_text(label, sheet_name), fmt)
                                else:
                                    ws.write_string(row_index, 0, _checked_text(label, sheet_name), fmt)
                                ws.set_row(row_index, 29 if kind == 'section' else 25)
                                row_index += 1
                                if kind == 'section':
                                    group_ordinal = 0
                                    explicit_group = False
                                elif kind == 'group':
                                    number = label.split(' ', 2)[1]
                                    if not number.isdigit():
                                        raise ValueError(f'Invalid duplicate display group number: {label}')
                                    group_ordinal = int(number)
                                    explicit_group = True
                                    first_in_group = True
                            next_sheet()
                            for row in reader:
                                if len(row) > len(header):
                                    raise ValueError(f'{sheet_name}: result row exceeds the public column count.')
                                if len(row) < len(header):
                                    row.extend([''] * (len(header) - len(row)))
                                # Sequential CSV has *non-beneficiary* visual heading rows.
                                # Preserve only four public Excel sheets and public fields.
                                first_cell = row[0].strip() if row else ''
                                heading_only = (not summary and sheet_name in
                                    ('DUPLICATE RECORDS','RECORDS FOR REVIEW') and
                                    not any(value.strip() for value in row[1:]))
                                if heading_only and first_cell.startswith(('SECTION 1 — ', 'SECTION 2 — ')):
                                    active_section = first_cell
                                    active_group = ''
                                    put_heading(first_cell, 'section')
                                    continue
                                if heading_only and duplicate and first_cell.startswith('GROUP '):
                                    # The Sequential CSV uses these rows only as
                                    # verified, internal group boundaries. Keep
                                    # exact colors and order without rendering
                                    # any numbered GROUP heading in the XLSX.
                                    active_group = first_cell
                                    parts = first_cell.split(' ', 2)
                                    if len(parts) < 3 or not parts[1].isdigit():
                                        raise ValueError('Invalid duplicate display group metadata.')
                                    group_ordinal = int(parts[1])
                                    explicit_group = True
                                    first_in_group = True
                                    continue
                                if heading_only and first_cell == 'No matching records in this section.':
                                    put_heading(first_cell, 'empty')
                                    continue
                                if row_index >= EXCEL_MAX_ROWS:
                                    next_sheet()
                                    if active_section:
                                        # Repeated section label is visible on continuation,
                                        # but the current group identity must survive a
                                        # worksheet split without a GROUP heading row.
                                        previous_group=(group_ordinal,first_in_group,explicit_group)
                                        put_heading(active_section + ' (continued)', 'section')
                                        group_ordinal,first_in_group,explicit_group=previous_group
                                        # Numbered group rows remain metadata only.
                                if summary:
                                    fmt = (overall_summary_fmt if row and row[0].upper() == 'OVERALL FINAL RESULT'
                                           else regular_summary_fmt)
                                    ws.write_string(row_index, 0, _checked_text(row[0], sheet_name), fmt)
                                    for col in range(1, 5):
                                        value = row[col].strip()
                                        if value and (not value.isascii() or not value.isdecimal()):
                                            raise ValueError(f'Invalid Summary count in column {col + 1}.')
                                        ws.write_number(row_index, col, int(value or 0), fmt)
                                    if int(row[1]) != sum(int(v) for v in row[2:5]):
                                        raise ValueError('Summary File A classification counts are inconsistent.')
                                    ws.set_row(row_index, 27 if fmt is overall_summary_fmt else 23)
                                elif duplicate:
                                    if explicit_group:
                                        first = first_in_group
                                        first_in_group = False
                                    else:
                                        first = _group_first(row, dtype_idx, reason_idx, group_ordinal)
                                        if first:
                                            group_ordinal += 1
                                    marker = row[dtype_idx]
                                    is_reference = marker.startswith('REFERENCE (FILE ')
                                    style_key = ((group_ordinal - 1) % 5, first, is_reference)
                                    style = row_styles[style_key]
                                    for col, value in enumerate(row):
                                        value = _checked_text(value, sheet_name)
                                        cell_style = (classification_styles.get(style_key + (marker,), style)
                                                      if col == dtype_idx else style)
                                        if value:
                                            ws.write_string(row_index, col, value, cell_style)
                                        else:
                                            ws.write_blank(row_index, col, None, cell_style)
                                    logical_lines = sum(max(1, (len(part) + 68) // 69)
                                                        for part in row[reason_idx].split('\n'))
                                    ws.set_row(row_index, min(115,
                                        max(24 if is_reference else 35, logical_lines * 16 + 9)))
                                else:
                                    style = validated_fmt if sheet_name == 'VALIDATED RECORDS' else review_fmt
                                    for col, value in enumerate(row):
                                        value = _checked_text(value, sheet_name)
                                        if value:
                                            ws.write_string(row_index, col, value, style)
                                        else:
                                            ws.write_blank(row_index, col, None, style)
                                    if sheet_name == 'RECORDS FOR REVIEW':
                                        ws.set_row(row_index, 30)
                                row_index += 1
            os.replace(temporary, output_path)
            return output_path
        finally:
            temporary.unlink(missing_ok=True)
