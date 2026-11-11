# qax

**Self-healing QA regression automation**: an Excel test-case workbook →
executed Playwright (JS) browser tests → `results.json`, driven by an
embedded agent core that generates cases, repairs broken tests after app
updates, and reports.

Fully self-contained: `uv` + Python for the CLI, Node.js for the Playwright
runner (provisioned automatically under `~/.qax`), Chromium downloaded on
first run. No cloud, no external services beyond your LLM provider key.

## Pipeline

```
qax plan    phase-1: recon + agent-generated test cases (Excel workbook)
qax run     Excel test cases -> Playwright JS specs -> executed -> results.json
qax heal    agent repairs failed specs after an app update (never app code)
qax report  render results.json as a human-readable summary
```

### Workflow

1. **`qax init`** — bootstrap `~/.qax` (config, secrets template, bundled
   skills, Node/Playwright runtime). Add your provider key to `~/.qax/.env`.
2. **`qax doctor`** — health-check everything.
3. **`qax plan --project <dir> [--app-url https://...]`** — when the project
   has no test suites: recon agent, then 3 parallel agents produce
   requirements / user stories / unit tests + open questions
   (`automation/questions.json`). Answer them (`qax plan --continue`
   interactively, or `qax plan --answers answers.json`), and per-story
   agents generate `test_cases.xlsx`.
4. **`qax run --workbook test_cases.xlsx [--headed]`** — compiles the
   workbook into Playwright JS specs (`automation/tests/`), runs them
   (chromium), and writes `automation/results.json`. `--headed` shows a
   visible browser for manual verification.
5. **`qax run --vibe-audit --app-url <url> [--headed]`** — the Vibe Audit
   suite: axe-core WCAG 2.x A/AA scan, text & UI contrast (WCAG 1.4.3 /
   1.4.11 ratios), heading order, keyboard focus visibility, touch-target
   size, emoji-only icon buttons, `prefers-reduced-motion` compliance,
   mobile-viewport overflow, and theme-consistency census. Audit failures
   are treated as real app defects (never auto-healed). Can be combined
   with `--workbook` to run functional + audit cases in one pass.
6. **`qax heal`** — for every failed case, the embedded agent reads the
   failure + app git diff, inspects the live DOM, patches ONLY the spec,
   re-runs, and records the healing. `--regenerate` on `qax run` rebuilds
   specs when the workbook changed.
6. **`qax report`** — pass/fail summary + bug list.

## Requirements

- Python 3.11–3.13 + [uv](https://docs.astral.sh/uv/)
- Node.js 18+ (LTS recommended) — the JS Playwright runner installs itself
  into `~/.qax/node` on first `qax init`; Chromium is downloaded once.

## Install

```bash
uv sync                 # dev: creates .venv, qax on PATH via uv run
# or globally:
uv tool install --python 3.13 .
```

## Excel workbook format

One sheet per suite; one row per test case:

| case_id | suite | title | steps | expected_result | severity | priority |
|---|---|---|---|---|---|---|
| TC-001 | auth | Login with valid credentials | 1. Open https://app.example.com<br>2. Fill Username with admin<br>3. Fill Password with secret<br>4. Click Login<br>5. Expect Welcome is visible | Welcome page loads | High | P1 |

Steps: one action per numbered line. Supported grammar: `open/go to/navigate
to <url>`, `click <target> [N times]`, `fill <target> with <value>`,
`select <value> from <target>`, `check/uncheck/clear/hover <target>`,
`press <key> [on <target>]`, `wait for <target>`, `expect <text> is visible`,
`expect url contains <fragment>`, `expect text <text>`, `wait N`,
`screenshot [name]`. Anything else becomes a `// TODO(manual)` line that the
healer can complete.

Selectors are resolved with a resilient strategy (test-id → role/name →
label → placeholder → text → token-fuzzy), so generated specs survive minor
UI drift; the healer repairs the rest.

## Self-healing

`qax heal` runs the embedded agent per failure with the `qa-self-healing`
skill: it checks the app's git diff to distinguish UI drift from intentional
behavior change (or a genuine regression — which it reports, never hides),
inspects the live DOM, patches only files under `automation/tests/`, and
re-verifies. Only a verified re-run marks a case `healed` in `results.json`.

## Project layout

```
automation/
  tests/            generated Playwright JS specs + helpers.js (gitignored)
  reports/<run_id>/ per-run: JSON report, log, artifacts/ (screenshots)
  questions.json    open questions from the generation phase
  answers.json      your answers (batch mode)
  state.json        persisted plan state (app URL, ...)
  results.json      latest run results
test_cases.xlsx     the workbook (checked into the repo)
```

## License

MIT — see [LICENSE](LICENSE).
