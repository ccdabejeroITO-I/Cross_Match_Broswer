"""Shared desktop v6.33-compatible Excel export styling.

Ported from the actual `export_results` and `_merge_sequential_workbook`
XlsxWriter formatting blocks in CrossMatch_v6_33_Multipass_Fuzzy_Recall.py.
Only presentation logic is shared; Web-specific identity classification,
mandatory-DOB precedence, and reference handling remain in the Web engine.
"""
from __future__ import annotations

HEADER_STYLE = {"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78",
                "border": 1, "border_color": "#8EA9C1", "align": "center",
                "valign": "vcenter", "text_wrap": True}
VALIDATED_FILL = "#F3F8FC"
REVIEW_FILL = "#FCE8E6"
OVERALL_FILL = "#DCE9F5"
# The literal palette and type colors come from desktop v6.33 export_results().
GROUP_PALETTE = ("#E3F4E8", "#F0E7FC", "#E5F1FD", "#FFF0DF", "#FBE7EF")
CLASS_PALETTE = {
    "TRUE_DUPLICATE": "#A8E2B9", "TRUE_SWAP_DUPLICATE": "#A8CFF6",
    "FUZZY_DUPLICATE": "#FFE5A0", "FUZZY_SWAP_DUPLICATE": "#F8C7AA",
}
SUMMARY_COLUMNS = ("Processing Stage", "Total File Records", "VALIDATED RECORDS",
                   "DUPLICATE RECORDS", "RECORDS FOR REVIEW")
PUBLIC_FIELDS = ("DedupType", "MatchPercentage", "ConflictReason")


def make_group_formats(workbook):
    """Constant-size format cache using v6.33's group/family style logic.

    For a family the entire row retains a common background; only DedupType
    gets the classification color. This follows the desktop public workbook.
    """
    row_styles, type_styles = {}, {}
    for shade_index, shade in enumerate(GROUP_PALETTE):
        for first in (False, True):
            for reference in (False, True):
                props = {"bg_color": shade, "bold": reference,
                         "valign": "top", "text_wrap": True}
                if first:
                    props.update({"top": 2, "top_color": "#305496"})
                key = (shade_index, first, reference)
                row_styles[key] = workbook.add_format(props)
                for label, fill in CLASS_PALETTE.items():
                    type_styles[key + (label,)] = workbook.add_format({**props, "bg_color": fill})
    return row_styles, type_styles


def put_summary(workbook, rows):
    """Write desktop v6.33's five-column Summary, including stage rows.

    'rows' is [(stage, original_file_a_count_for_stage, validated, dup, review)].
    No File B reference row is ever added to a classification total.
    """
    ws = workbook.add_worksheet("SUMMARY")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 0)
    ws.set_column("A:A", 38)
    ws.set_column("B:E", 25)
    ws.write_row(0, 0, SUMMARY_COLUMNS, workbook.add_format(HEADER_STYLE))
    ws.set_row(0, 28)
    overall = workbook.add_format({"num_format": "#,##0", "valign": "vcenter",
                                   "bold": True, "bg_color": OVERALL_FILL})
    normal = workbook.add_format({"num_format": "#,##0", "valign": "vcenter"})
    for ix, (stage, n, valid, dup, review) in enumerate(rows, 1):
        if int(n) != int(valid) + int(dup) + int(review):
            raise ValueError(f"Summary classification integrity error in {stage}")
        fmt = overall if str(stage).upper() == "OVERALL FINAL RESULT" else normal
        ws.write(ix, 0, str(stage), fmt)
        for col, number in enumerate((n, valid, dup, review), 1):
            ws.write_number(ix, col, int(number), fmt)
        ws.set_row(ix, 27 if fmt is overall else 23)
    return ws
