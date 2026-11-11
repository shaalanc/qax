"""Build results.json from the Playwright JSON report + workbook metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from qax.excel_parser import TestCase

RESULTS_SCHEMA_VERSION = 1


def _walk_specs(node: dict):
    """Recursively yield ``(suite_title, spec)`` pairs from the report tree."""
    for suite in node.get("suites", []):
        yield from _walk_specs(suite)
        for spec in suite.get("specs", []):
            yield suite.get("title", ""), spec


def _spec_status(spec: dict) -> tuple[str, str | None, str | None]:
    tests = spec.get("tests") or []
    if not tests:
        return "skipped", None, None
    t = tests[0]
    st = t.get("status", "unexpected")
    # The Playwright JSON reporter nests per-attempt results (and their
    # errors/attachments) under `tests[].results[]`.
    result = (t.get("results") or [{}])[0]
    err_obj = result.get("error") or {}
    msg = err_obj.get("message") or err_obj.get("value") or "test failed"
    screenshot = None
    for att in result.get("attachments") or []:
        p = att.get("path")
        if p and (att.get("name") == "screenshot" or str(p).endswith(".png")):
            screenshot = str(p)
            break
    if st == "expected":
        return "passed", None, screenshot
    if st == "flaky":
        return "passed", "flaky: passed after retries", screenshot
    if st == "skipped":
        return "skipped", None, screenshot
    return "failed", str(msg)[:1000], screenshot


def build_results(
    run_id: str,
    commit: str,
    report_path: Path,
    cases: list[TestCase],
    healing_notes: dict[str, str] | None = None,
) -> dict:
    """Assemble the full results document from a Playwright JSON report.

    Test titles carry the workbook case id as their first token
    (``TC-001 | ...``), which is how specs map back to the workbook.
    """
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    healing_notes = healing_notes or {}
    by_case = {c.case_id: c for c in cases}

    results: list[dict] = []
    for suite_title, spec in _walk_specs(data):
        title = spec.get("title") or ""
        case_id = title.split("|", 1)[0].strip()
        status, error, screenshot = _spec_status(spec)
        case = by_case.get(case_id)
        entry: dict = {
            "case_id": case_id,
            "suite": case.suite if case else suite_title,
            "status": status,
            "error": error,
            "screenshot": screenshot,
            "healed": False,
            "healing_note": None,
        }
        if case:
            entry["title"] = case.title
            entry["severity"] = case.severity
            entry["priority"] = case.priority
            entry["expected_result"] = case.expected_result
        note = healing_notes.get(case_id)
        if note:
            entry["healing_note"] = note
            # Status ALWAYS comes from the verification re-run (report).
            # A note only adds context; only a HEALED note marks the flag.
            if note.startswith("HEALED"):
                entry["healed"] = True
        results.append(entry)

    total = len(results)
    summary = {
        "total": total,
        "passed": sum(1 for r in results if r["status"] == "passed"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "healed": sum(1 for r in results if r.get("healed")),
    }

    return {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "run_id": run_id,
        "commit": commit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "results": results,
        "bugs": [
            {k: r.get(k) for k in ("case_id", "suite", "severity", "priority", "error")}
            for r in results
            if r["status"] == "failed"
        ],
    }


def save_results(results: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")


def load_results(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
