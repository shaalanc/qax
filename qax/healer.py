"""Self-healing orchestrator.

For each failed case, the embedded agent (with the ``qa`` toolset) receives
the failure + spec path + the qa-self-healing skill, inspects the live DOM,
patches ONLY files under ``automation/tests/``, and re-runs the test itself.
The orchestrator verifies the outcome and records healing notes.
"""

from __future__ import annotations

from pathlib import Path

from qax.agent_core import run as agent_run
from qax.runner import run_single_test, single_test_command

MAX_HEAL_ATTEMPTS = 2

_HEAL_PROMPT = """You are qax's self-healing agent. A generated Playwright (JS) test is failing
after an app update. Your job: repair the TEST (never the application).

Case: {case_id} ({suite})
Spec file: {spec_file}
Failure (first 800 chars):
{error}

Procedure (follow the qa-self-healing skill):
1. Read the spec file and the failing test.
2. Read the app's git diff since the last green run to judge intent: UI
   changed (heal the selector) vs behavior intentionally changed (update the
   expectation). If the app is genuinely REGRESSED, do NOT patch a test to
   hide it — report that instead.
3. If it is a locator/selector issue, inspect the live DOM in a real browser
   (browser_exec) and find the replacement selector.
4. Patch ONLY files under {tests_dir} — never anywhere else in the project.
5. Re-run the single test yourself with this exact command:
   {rerun_cmd}
   Iterate until green or give up after {attempts} attempts.
6. Final response: one short paragraph — what broke, what you changed, and
   the final test outcome. Prefix with HEALED: if the test now passes,
   otherwise UNHEALED: with the reason."""


def find_spec_for_case(tests_dir: Path, case_id: str) -> Path | None:
    """Locate the spec file containing the case's test (by case id token)."""
    for f in tests_dir.glob("*.spec.js"):
        text = f.read_text(encoding="utf-8")
        if f'"{case_id} |' in text or f"'{case_id} |" in text:
            return f
    return None


def heal_case(
    case_id: str,
    suite: str,
    error: str,
    project: Path,
    tests_dir: Path,
    reports_dir: Path,
    run_id: str,
) -> str | None:
    """Run the healing agent for one case. Returns a healing note or None."""
    spec_file = find_spec_for_case(tests_dir, case_id)
    if spec_file is None:
        return f"UNHEALED: no spec file found for {case_id}"
    rerun_cmd = single_test_command(tests_dir, case_id, reports_dir, f"{run_id}_heal_{case_id}")
    prompt = _HEAL_PROMPT.format(
        case_id=case_id,
        suite=suite,
        spec_file=spec_file,
        error=(error or "")[:800],
        tests_dir=tests_dir,
        rerun_cmd=rerun_cmd,
        attempts=MAX_HEAL_ATTEMPTS,
    )
    try:
        response, _result = agent_run(prompt, toolsets=["qa"])
    except Exception as exc:
        return f"UNHEALED: healer agent failed: {exc}"

    # Verify independently: did the test actually go green?
    rc = run_single_test(tests_dir, case_id, project, reports_dir, f"{run_id}_heal_{case_id}")
    outcome = "HEALED" if rc == 0 else "UNHEALED"
    response = (response or "").strip()
    if response.startswith(("HEALED:", "UNHEALED:")):
        response = response.split(":", 1)[1].strip()
    return f"{outcome}: {response[:500]}"
