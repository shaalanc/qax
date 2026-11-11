"""Excel test-case workbook parser.

Expected workbook: one row per test case, header row with columns:
    case_id | suite | title | steps | expected_result | severity | priority

``steps`` is a single cell containing numbered lines, one action per line:
    "1. Open https://example.com/login"
    "2. Fill Username with admin"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

REQUIRED_COLUMNS = {"case_id", "suite", "title", "steps"}
OPTIONAL_COLUMNS = {"expected_result", "severity", "priority"}


@dataclass
class TestCase:
    case_id: str
    suite: str
    title: str
    steps: list[str] = field(default_factory=list)
    expected_result: str = ""
    severity: str = "normal"
    priority: str = "medium"


def _normalize_header(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _split_steps(cell: object) -> list[str]:
    """Split a steps cell into clean action lines (strip numbering/bullets)."""
    if cell is None:
        return []
    lines: list[str] = []
    for line in str(cell).splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^(step\s*)?\d+[.)]\s*", "", line, flags=re.IGNORECASE)
        line = line.lstrip("- ").strip()
        if line:
            lines.append(line)
    return lines


def parse_workbook(path: str | Path) -> list[TestCase]:
    """Parse the workbook into TestCase objects. Raises ValueError on a
    missing required column or an empty workbook."""
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"workbook is empty: {path}")
    headers = [_normalize_header(h) for h in rows[0]]
    header_index = {name: i for i, name in enumerate(headers)}
    missing = REQUIRED_COLUMNS - header_index.keys()
    if missing:
        raise ValueError(
            f"workbook missing required columns: {sorted(missing)} "
            f"(found: {[h for h in headers if h]})"
        )

    def get(row: tuple, name: str) -> str:
        i = header_index.get(name)
        if i is None or i >= len(row):
            return ""
        v = row[i]
        return str(v).strip() if v is not None else ""

    cases: list[TestCase] = []
    for row in rows[1:]:
        if not row or all(c is None for c in row):
            continue
        case_id = get(row, "case_id")
        suite = get(row, "suite")
        if not case_id or not suite:
            continue
        cases.append(
            TestCase(
                case_id=case_id,
                suite=suite,
                title=get(row, "title") or case_id,
                steps=_split_steps(get(row, "steps")),
                expected_result=get(row, "expected_result"),
                severity=get(row, "severity") or "normal",
                priority=get(row, "priority") or "medium",
            )
        )
    return cases
