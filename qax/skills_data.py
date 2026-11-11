"""Bundled qax skills.

These SKILL.md documents are installed into QAX_HOME/skills/ on ``qax init``.
The embedded agent core discovers them automatically on every run, so they are
the project's procedural memory: they define HOW qax runs regression and HOW
it heals specs.

``bundled_skill_dirs()`` skills are copied from ``qax/skills_bundle/`` and
carry reference files (full QA methodology in ``qa-rules``).
"""

from pathlib import Path

SKILLS: dict[str, str] = {
    "qa-automation-runner": """---
name: qa-automation-runner
description: Use when running qax regression: read the Excel test-case workbook, generate Playwright specs per suite, execute them, and write results.json.
---

# qax Automation Runner

The master procedure for turning the test-case workbook into executed
Playwright tests and a results report.

## Trigger
- `qax run` invoked, or a regression pass requested after an app update.

## Procedure
1. Locate the workbook: `<project>/test_cases.xlsx` (override with
   `qax run --workbook <path>`).
2. Read it: one row per test case, columns
   `case_id | suite | title | steps | expected_result | severity | priority`.
   Steps are numbered lines inside one cell; one action per line.
3. `qax run` groups cases by `suite` and generates one spec per suite at
   `<project>/automation/tests/suite_<suite>.spec.js` (Playwright test
   runner, one `test('<case_id> | ...')` per case) plus a shared
   `helpers.js` with resilient locator resolution. Rebuild with
   `--regenerate`.
4. Steps are compiled by a deterministic grammar: open/go to, click,
   fill X with Y, select Z from X, check/uncheck, clear, hover, press,
   wait for, expect <text> is visible, expect url contains, screenshot,
   wait N. Anything else becomes a `// TODO(manual)` line for the healer.
5. Execute: `qax run` invokes the Playwright (JS) runner (chromium, JSON
   report) with failure screenshots into
   `<project>/automation/reports/<run_id>/`.
6. Results land in `<project>/automation/results.json` (schema below),
   enriched with severity/priority from the workbook; `qax report` renders
   it human-readable. Exit code 1 when any case failed.
7. Vibe Audit suite (`qax run --vibe-audit --app-url <url>`): axe-core WCAG
   scan, text/UI contrast, heading order, focus visibility, touch-target
   size, emoji-only buttons, reduced-motion, mobile overflow, theme census.
   Failures = real app defects; `qax heal` skips this suite by design.
8. On failure, consult the qa-self-healing skill before declaring a bug
   (`qax heal` runs it automatically).

## results.json schema
```json
{"schema_version": 1, "run_id": "...", "commit": "...", "timestamp": "...",
 "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "healed": 0},
 "results": [{"case_id": "...", "suite": "...", "status": "passed|failed|skipped",
              "severity": "...", "priority": "...", "error": null,
              "screenshot": null, "healed": false, "healing_note": null}],
 "bugs": [{"case_id": "...", "severity": "...", "error": "..."}]}
```

## Generation phase (no test suites exist)

`qax plan` on a suite-less project: deterministic scan -> recon agent
(recon.md) -> 3 PARALLEL agents (requirements / user_stories / unit_tests),
each writing `automation/artifacts/<name>.md` + `<name>.questions.json`
(STRICT no-assumptions rule) -> merged `automation/questions.json`.
Then the human-in-the-loop: `qax plan --continue` (interactive) or
`qax plan --answers answers.json` ({id: answer}) -> answers appended to the
.md files -> per-story test-case agents (parallel, one per story in
`user_stories.json`) -> merged `test_cases.xlsx` -> `qax run`.
Generation agents never modify project files outside `automation/`.

## Test-case writing rules (full methodology: the qa-rules skill)

- Cover per story: happy path, negative cases, edge/boundary, and state
  variants (repeat, stale, cancelled, expired). Security/trust probes
  (auth, authorization, tenant isolation, data integrity) come first
  (P0/P1).
- Expected results MUST be observable and precise: exact message, value,
  state, side effect — never "works correctly" or "should work".
- Never invent business rules. Ambiguity becomes an open question in the
  generation phase, or an explicit "(assumption)" note in the case.
- Every critical story needs at least one negative and one boundary case.
- A green run proves the executed cases passed — not correctness beyond
  what was tested; report scope and residual risk.

## Pitfalls
- Never modify application code — only files under `automation/tests/`.
- Keep test data lifecycle: create -> use -> remove/archive under
  `automation/data/`. Never leave test records in the app.
- A failing case after an update is NOT automatically a bug: check the git
  diff and the user story first (see qa-self-healing skill).
- Specs are `*.spec.js` files; each test title starts with the workbook
  case id (`TC-001 | ...`), which the reporter maps back to the workbook.
""",
    "qa-self-healing": """---
name: qa-self-healing
description: Use when a generated Playwright spec fails after a code update — inspect the live DOM, patch the spec, re-run, and record the fix.
---

# qax Self-Healing

The procedure for repairing automation after the application changes.

## Trigger
- A spec under `automation/tests/` fails with a locator/selector error
  (TimeoutError, strict-mode violation, element not found), or expected
  behavior changed.

## Procedure
1. Read the failure trace — identify the exact selector that broke.
2. Read the app's git diff since the last green run (`git log`/`git diff`)
   and the originating user story to judge intent:
   - UI changed but behavior is the same  → the test is wrong: heal it.
   - Behavior intentionally changed      → update the test's expectations
     (and note it; do not silently "fix" a regression).
3. Inspect the live DOM with `browser_exec` (drive the real browser,
   read the accessibility tree / CSS selectors) to find the replacement
   selector.
4. Patch ONLY files under `automation/tests/**` with the `patch` tool.
5. Re-run the single spec; iterate until green.
6. Record the healing: set `healed: true` + a `healing_note` in
   results.json, and update memory with the new stable selector.

## Pitfalls
- Never patch application code to make a test pass.
- Never blanket-retry; a healer that re-runs without changing anything is a
  lie detector, not a healer.
- If the DOM inspection shows the feature is genuinely broken (regression),
  stop healing and file a bug with evidence (screenshot + trace).
""",
}


def skill_files() -> dict[str, str]:
    """Map skill name -> SKILL.md content for installation."""
    return SKILLS


def bundled_skill_dirs() -> dict[str, Path]:
    """Map skill name -> repo directory holding SKILL.md + references/.

    Directory-based skills are copied wholesale by ``qax init`` so their
    reference files (e.g. the qa-rules methodology bundle) install too.
    """
    return {
        "qa-rules": Path(__file__).resolve().parent / "skills_bundle" / "qa-rules",
    }
