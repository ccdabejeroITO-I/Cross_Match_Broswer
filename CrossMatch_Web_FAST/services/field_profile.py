"""Safe, bounded field type hints for the authenticated Rule Builder.

Types are only UI recommendations. Saved rules and actual matching always use
explicit operators; no implicit type conversion of identifiers occurs.
"""
from __future__ import annotations

from contextlib import closing
from itertools import islice
from pathlib import Path
import re

from engine import crossmatch_engine as engine
from services.session_manager import session_dir
from services.value_suggestions import _column_values

_DATE_RE = re.compile(r"^(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,12}\s+\d{4}|[A-Za-z]{3,12}\s+\d{1,2},?\s+\d{4})(?:\s+.*)?$")
_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_DATE_HEADER_RE = re.compile(r"(^|\W)(?:date|dob|birthdate|birthday|timestamp|created_at|updated_at|paid_at|dateofbirth|date_of|dated)(\W|$)")
_NUMBER_HEADER_RE = re.compile(r"(^|\W)(?:age|amount|total|count|quantity|qty|price|score|income|salary|balance|birth_year|birth_month|birth_day)(\W|$)")
_IDENTIFIER_RE = re.compile(r"(?:^|\W)(?:id|hhid|identifier|code|phone|mobile|contact|account|serial|reference|postal|zip|number)(?:\W|$)")


def _hint(name: str) -> str:
    h = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).casefold()
    if _IDENTIFIER_RE.search(h):
        return 'text'  # Never treat HHIDs and similar codes as numbers.
    if _DATE_HEADER_RE.search(h):
        return 'date'
    if _NUMBER_HEADER_RE.search(h):
        return 'number'
    return 'text'


def _classify(header: str, values: list[str]) -> dict:
    hint = _hint(header)
    valid = [str(v).strip() for v in values if v is not None and str(v).strip() and str(v).strip().casefold() not in {'nan','null','none','n/a'}]
    if not valid:
        return {'kind': hint, 'basis': 'column name' if hint != 'text' else 'default', 'sampled': 0}
    dates = sum(bool(_DATE_RE.fullmatch(v)) for v in valid)
    numeric = sum(bool(_NUMBER_RE.fullmatch(v)) for v in valid)
    padded_ids = any(re.match(r'^[+-]?0\d{2,}$', v) for v in valid)
    threshold = 0.8 * len(valid)
    # Identifier headers trump numeric-looking values and preserve leading zeros.
    if _IDENTIFIER_RE.search(re.sub(r'([a-z])([A-Z])',r'\1_\2',header).casefold()):
        kind = 'text'
    elif dates >= threshold:
        kind = 'date'
    elif padded_ids:
        kind = 'text'
    elif numeric >= threshold:
        kind = 'number'
    elif hint == 'date' and dates:
        kind = 'date'
    elif hint == 'number' and numeric:
        kind = 'number'
    else:
        kind = 'text'
    return {'kind': kind, 'basis': 'uploaded values', 'sampled': len(valid)}


def profile_for_file(session_id: str, side: str, file_info: dict, header: str) -> dict:
    if header not in file_info.get('headers', []):
        raise ValueError('Selected column does not exist in this uploaded file.')
    source = Path(file_info['server_path']).resolve()
    expected_dir = (session_dir(session_id) / 'uploads').resolve()
    if source.parent != expected_dir or not source.is_file():
        raise ValueError('Uploaded file is missing or does not belong to this session.')
    plan = engine.inspect_input(source, file_info.get('sheet') if source.suffix.casefold() != '.csv' else None)
    if header not in plan.headers:
        raise ValueError('Column is no longer present in the selected worksheet.')
    # At most 1500 early rows; stop as soon as 70 meaningful values are obtained.
    found=[]
    with closing(_column_values(plan, header)) as rows:
        for raw in islice(rows, 1500):
            value=str(raw if raw is not None else '').strip()
            if value:
                found.append(value)
                if len(found) >= 70:
                    break
    return _classify(header, found)
