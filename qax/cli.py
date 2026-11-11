#!/usr/bin/env python3
"""qax CLI — QA test automation on an embedded agent core.

Commands
--------
init     Bootstrap the qax home (~/.qax): config, secrets file, bundled skills.
doctor   Health-check the qax environment (config, keys, skills, deps).
plan     Phase 1 recon: understand the project, check for test suites, and
         (when none exist) spawn the 3 background agents producing the
         requirements/user-stories/unit-test .md files + questions.json.
run      Regression run: Excel test cases -> Playwright specs -> results.json.
heal     Self-healing pass over failed specs after a code update.
report   Render automation/results.json as a human-readable summary.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path


def _sanitize_import_env() -> None:
    """A self-contained fork must not inherit a polluted import environment.

    The parent process (a desktop app or a machine with another agent CLI
    installed) may export PYTHONPATH pointing at ITS OWN checkout and venv.
    Those entries would shadow qax's vendored core modules (toolsets,
    agent, ...). Keep only the qax checkout root, qax's own venv, and the
    stdlib; drop everything else.
    """
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    prefix = Path(sys.prefix).resolve()
    base = Path(sys.base_prefix).resolve()
    root = Path(__file__).resolve().parent.parent
    kept = []
    for entry in sys.path:
        if not entry or entry in (".", ""):
            kept.append(entry)
            continue
        try:
            p = Path(entry).resolve()
        except Exception:
            kept.append(entry)
            continue
        if p == root or p.is_relative_to(root) or p.is_relative_to(prefix) or p.is_relative_to(base):
            kept.append(entry)
    sys.path[:] = kept


_sanitize_import_env()

from qax import __version__
from qax.home import ensure_env, ensure_home, install_default_config, qax_home, set_hermes_home_env

# HERMES_HOME must point at the qax home before ANY hermes module import.
set_hermes_home_env()

# QAX_HOME_ISOLATION: the embedded core never sees another install.
os.environ.setdefault("HERMES_PROFILE", "default")


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #
def cmd_init(args: argparse.Namespace) -> int:
    home = ensure_home()
    cfg = install_default_config(home)
    env = ensure_env(home, copy_from_hermes=args.copy_env_from)
    mirrored = False
    if args.copy_env_from:
        from qax.home import mirror_hermes_model_config

        mirrored = mirror_hermes_model_config(home)
    installed = _install_bundled_skills(home)
    try:
        from qax.home import ensure_node_runtime

        node, _cli = ensure_node_runtime(home)
        print(f"node     : {node}")
    except RuntimeError as exc:
        print(f"node     : {exc}")
    print(f"qax home : {home}")
    print(f"config   : {cfg} {'(kept)' if cfg.exists() else '(created)'}")
    if mirrored:
        print("model    : mirrored from previous install (provider + default model)")
    print(f"secrets  : {env} {'(kept)' if env.exists() else '(created)'}")
    print(f"skills   : {', '.join(installed) or '(none)'}")
    print("\nNext: add your provider key to the secrets file, then run `qax doctor`.")
    return 0


def _install_bundled_skills(home: Path) -> list[str]:
    from qax.skills_data import bundled_skill_dirs, skill_files

    installed: list[str] = []
    skills_root = home / "skills" / "qa"
    # Inline skills (string content) — overwrite when the bundled source changed.
    for name, content in skill_files().items():
        target = skills_root / name / "SKILL.md"
        if target.exists() and target.read_text(encoding="utf-8") == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        installed.append(name)
    # Directory skills (SKILL.md + references/) — copy wholesale on change.
    for name, src_dir in bundled_skill_dirs().items():
        dst_dir = skills_root / name
        if _dirs_equal(src_dir, dst_dir):
            continue
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        installed.append(name)
    return installed


def _dirs_equal(a: Path, b: Path) -> bool:
    """True when every file under ``a`` exists byte-identical under ``b``."""
    if not b.exists():
        return False
    for fa in a.rglob("*"):
        if not fa.is_file():
            continue
        fb = b / fa.relative_to(a)
        if not fb.exists() or fa.read_bytes() != fb.read_bytes():
            return False
    return True


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #
def cmd_doctor(args: argparse.Namespace) -> int:
    home = qax_home()
    ok = True

    def check(label: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and good
        print(f"[{'OK ' if good else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))

    check("qax home exists", home.exists(), str(home))
    check("config.yaml present", (home / "config.yaml").exists())
    secrets = ensure_env(home)
    key_found = False
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line and not line.startswith("="):
                key_found = True
                break
    check("provider key in .env", key_found, str(secrets) if secrets.exists() else "missing")

    from qax.skills_data import bundled_skill_dirs, skill_files

    expected_skills = list(skill_files()) + list(bundled_skill_dirs())
    missing_skills = [
        n for n in expected_skills if not (home / "skills" / "qa" / n / "SKILL.md").exists()
    ]
    check("bundled skills installed", not missing_skills, f"missing: {missing_skills}" if missing_skills else "")

    from qax.home import node_bin, node_runtime_dir

    node = node_bin()
    check("node.js runtime", bool(node), node or "not found — install LTS from nodejs.org")
    cli_js = node_runtime_dir(home) / "node_modules" / "@playwright" / "test" / "cli.js"
    check("@playwright/test installed", cli_js.exists(),
          "" if cli_js.exists() else "missing — run `qax init` (installs into ~/.qax/node)")
    ms_playwright = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    has_chromium = ms_playwright.exists() and any(
        p.name.startswith("chromium") for p in ms_playwright.iterdir()
    )
    check("chromium browser installed", has_chromium,
          "" if has_chromium else "missing — run `qax init` (downloads once)")
    try:
        import openpyxl

        check("python dep: openpyxl", True)
    except Exception:
        check("python dep: openpyxl", False, "not importable — run `uv sync`")

    try:
        import hermes_cli.oneshot  # noqa: F401

        check("embedded agent core imports", True)
    except Exception as exc:
        check("embedded agent core imports", False, str(exc)[:200])

    # qa toolset must resolve
    try:
        from toolsets import resolve_toolset

        tools = resolve_toolset("qa")
        check("qa toolset resolves", bool(tools), f"{len(tools)} tools")
    except Exception as exc:
        check("qa toolset resolves", False, str(exc)[:200])

    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# plan — phase-1 recon + generation (only when no test suites exist)
# --------------------------------------------------------------------------- #
_PLAN_PROMPT = """You are qax's phase-1 recon agent working inside a QA pipeline.

Project folder: {project}

Tasks:
1. Understand the project: what kind of app is it (web/mobile/CLI), stack, entry points, structure.
2. Check whether test suites already exist (tests/, *_test.py, playwright.config, spec/ dirs, etc.). Answer YES or NO with evidence paths.
3. Write your findings to {out_file} as a Markdown report with sections: Project Summary, Stack, Existing Test Suites (yes/no + evidence), Open Questions.

Rules:
- Do NOT assume anything about the project. Every ambiguity becomes an Open Question for the user.
- Do NOT modify any project files. Only write the report file.
- Keep the report factual and evidence-based (cite file paths)."""


def _find_existing_suites(project: Path) -> list[str]:
    """Deterministic scan for pre-existing test suites."""
    skip_dirs = {"node_modules", "dist", "build", ".git", ".venv", "__pycache__", ".next", ".cache"}

    def _walk():
        for root, dirs, files in os.walk(project):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                yield Path(root) / f

    found: list[str] = []
    for pat in ("tests", "test", "spec", "e2e", "cypress", "playwright", "__tests__"):
        for d in project.glob(f"*/{pat}"):
            if d.is_dir() and d.name not in skip_dirs:
                found.append(str(d))
    for f in _walk():
        name = f.name
        if (
            name.endswith(("_test.py", "_spec.py"))
            or name.startswith("test_")
            or name in ("conftest.py", "pytest.ini", "playwright.config.js",
                        "playwright.config.ts", "playwright.config.mjs",
                        "jest.config.js", "jest.config.ts", "vitest.config.js",
                        "cypress.config.js", "cypress.config.ts")
        ):
            found.append(str(f))
    return sorted(dict.fromkeys(found))


def cmd_plan(args: argparse.Namespace) -> int:
    project = Path(args.project or os.getcwd()).resolve()
    if not project.is_dir():
        print(f"error: project folder not found: {project}", file=sys.stderr)
        return 1
    out_dir = project / "automation"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.continue_ or args.answers:
        return _plan_human_in_loop(project, args)

    # Phase 0: deterministic suite check.
    suites = _find_existing_suites(project)
    if suites:
        print("test suites already exist — skipping generation. Run `qax run`.")
        for s in suites[:10]:
            print(f"  found: {s}")
        return 0

    # Phase 1: recon agent.
    out_file = out_dir / "recon.md"
    prompt = _PLAN_PROMPT.format(project=project, out_file=out_file)
    from qax.agent_core import run as agent_run

    print(f"phase-1 recon on {project} ...")
    try:
        response, _result = agent_run(prompt, toolsets=["qa"])
    except Exception as exc:
        print(f"error: recon agent failed: {exc}", file=sys.stderr)
        return 1
    print(response[:400])

    # Phase 2: three parallel generation agents.
    from qax.agents import _find_app_url, run_generation_agents

    # Persist the target app URL so the later human-in-the-loop phase
    # (which may run without --app-url) generates cases against the same site.
    app_url = args.app_url or _find_app_url(project)
    state_file = out_dir / "state.json"
    state_file.write_text(json.dumps({"app_url": app_url}), encoding="utf-8")

    print("\nno test suites found — spawning 3 generation agents (requirements / user stories / unit tests) ...")
    try:
        qpath = run_generation_agents(project, out_file)
    except Exception as exc:
        print(f"error: generation agents failed: {exc}", file=sys.stderr)
        return 1

    questions = json.loads(qpath.read_text(encoding="utf-8"))
    print(f"\n{len(questions)} open question(s) merged -> {qpath}")
    for q in questions:
        print(f"  [{q['id']}] ({q['source']}) {q['question']}")
    print("\nHuman-in-the-loop next:")
    print("  qax plan --continue                    # answer interactively")
    print("  qax plan --answers answers.json        # batch answers (JSON {id: answer})")
    return 0 if questions else 1


def _plan_human_in_loop(project: Path, args: argparse.Namespace) -> int:
    """Answer the open questions, update the .md files, then spawn per-story
    test-case agents producing test_cases.xlsx."""
    from qax.agents import (
        ANSWERS_FILE,
        QUESTIONS_FILE,
        apply_answers,
        interactive_answers,
        load_answers,
        run_story_case_agents,
    )

    qpath = project / "automation" / QUESTIONS_FILE
    if not qpath.exists():
        print(f"error: no {qpath} — run `qax plan` first", file=sys.stderr)
        return 1
    questions = json.loads(qpath.read_text(encoding="utf-8"))
    answers_path = project / "automation" / ANSWERS_FILE

    if args.answers:
        try:
            answers = load_answers(Path(args.answers))
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    else:
        try:
            answers = interactive_answers(questions, answers_path)
        except EOFError:
            print(
                "error: no interactive terminal available.\n"
                f"Create {answers_path} as JSON ({{id: answer}}) and re-run "
                "with `qax plan --answers answers.json`.",
                file=sys.stderr,
            )
            return 1

    print("\napplying answers ...")
    apply_answers(project, answers, questions)

    print("spawning per-story test-case agents ...")
    try:
        stored_url = None
        state_file = project / "automation" / "state.json"
        if state_file.exists():
            stored_url = json.loads(state_file.read_text(encoding="utf-8")).get("app_url")
        wb = run_story_case_agents(project, answers, app_url=args.app_url or stored_url)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"\ntest cases merged -> {wb}")
    print("next: `qax run --workbook test_cases.xlsx`")
    return 0


# --------------------------------------------------------------------------- #
# run / heal / report
# --------------------------------------------------------------------------- #
def _resolve_app_url(project: Path, args: argparse.Namespace, cases) -> str | None:
    """--app-url > automation/state.json > first 'open <http>' step in the workbook."""
    if getattr(args, "app_url", None):
        return args.app_url
    state = project / "automation" / "state.json"
    if state.exists():
        try:
            stored = json.loads(state.read_text(encoding="utf-8")).get("app_url")
            if stored:
                return stored
        except Exception:
            pass
    for c in cases:
        for step in c.steps:
            m = re.search(r"https?://\S+", step)
            if m:
                return m.group(0)
    return None


def _session_state_path(project: Path, args: argparse.Namespace) -> str | None:
    """--session-state override, else automation/session.json when present."""
    explicit = getattr(args, "session_state", None)
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = project / p
        return str(p)
    default = project / "automation" / "session.json"
    return str(default) if default.exists() else None


def cmd_run(args: argparse.Namespace) -> int:
    """Excel test cases (+ optional vibe audit suite) -> Playwright run -> results.json."""
    from datetime import datetime

    project = Path(args.project or os.getcwd()).resolve()
    wb_path = Path(args.workbook)
    if not wb_path.is_absolute():
        wb_path = project / args.workbook
    has_wb = wb_path.exists()

    if not has_wb and not args.vibe_audit:
        print(f"error: workbook not found: {wb_path}", file=sys.stderr)
        return 1

    from qax.audit_suite import audit_test_cases, write_audit_files
    from qax.excel_parser import parse_workbook
    from qax.reporters import build_results, save_results
    from qax.runner import git_commit, run_tests
    from qax.spec_generator import generate_specs

    wb_cases: list = []
    if has_wb:
        try:
            wb_cases = parse_workbook(wb_path)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if not wb_cases:
            print("error: workbook contains no test cases", file=sys.stderr)
            return 1

    tests_dir = project / "automation" / "tests"
    if wb_cases:
        written = generate_specs(wb_cases, tests_dir, force=args.regenerate)
        if written:
            print(f"generated {len(written)} spec file(s) in {tests_dir}")
        else:
            print(f"specs already present in {tests_dir} (use --regenerate to rebuild)")
    else:
        # Audit-only run: drop stale generated specs from earlier runs so the
        # results reflect exactly this invocation.
        from qax.audit_suite import SPEC_FILENAME as AUDIT_SPEC

        for stale in list(tests_dir.glob("suite_*.spec.js")) + list(tests_dir.glob("test_*.py")):
            if stale.name != AUDIT_SPEC:
                stale.unlink()
        print(f"audit-only run in {tests_dir} (stale specs pruned)")

    cases = list(wb_cases)
    if args.vibe_audit:
        url = _resolve_app_url(project, args, cases)
        if not url:
            print("error: --vibe-audit needs an app URL — pass --app-url <url> "
                  "(or run from a project with automation/state.json / a workbook)", file=sys.stderr)
            return 1
        audit_files = write_audit_files(url, tests_dir, force=args.regenerate)
        if audit_files:
            print(f"vibe audit suite ready ({len(audit_files)} file(s), target {url})")
        cases += audit_test_cases()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = project / "automation" / "reports" / run_id
    reports_dir.mkdir(parents=True, exist_ok=True)

    print(f"running {len(cases)} test case(s) ...")
    ss = _session_state_path(project, args)
    rc, report = run_tests(project, tests_dir, reports_dir, run_id,
                           headed=args.headed, storage_state=ss)
    results = build_results(run_id, git_commit(project), report, cases)
    out = project / "automation" / "results.json"
    save_results(results, out)

    s = results["summary"]
    print(f"\nrun {run_id}: total={s['total']} passed={s['passed']} "
          f"failed={s['failed']} skipped={s['skipped']}")
    for bug in results["bugs"]:
        print(f"  FAIL {bug['case_id']} [{bug['suite']}] {bug['error']}")
    print(f"results: {out}")
    return 0 if s["failed"] == 0 else 1


def cmd_heal(args: argparse.Namespace) -> int:
    """Self-heal failed specs after an app update (agent-driven)."""
    from datetime import datetime

    project = Path(args.project or os.getcwd()).resolve()
    results_path = project / "automation" / "results.json"
    if not results_path.exists():
        print(f"error: no results at {results_path} — run `qax run` first", file=sys.stderr)
        return 1

    from qax.healer import heal_case
    from qax.reporters import build_results, load_results, save_results
    from qax.runner import git_commit, run_tests

    data = load_results(results_path)
    tests_dir = project / "automation" / "tests"
    failed = [r for r in data["results"] if r["status"] == "failed"]
    if not failed:
        print("nothing to heal — no failed cases")
        return 0

    print(f"healing {len(failed)} failed case(s) ...")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_heal")
    reports_dir = project / "automation" / "reports" / run_id
    reports_dir.mkdir(parents=True, exist_ok=True)

    healing_notes: dict[str, str] = {}
    for r in failed:
        if r.get("suite") == "Vibe Audit":
            note = ("SKIPPED: audit failure = real app defect (WCAG/design). "
                    "Fix the app, then re-run `qax run --vibe-audit`.")
            healing_notes[r["case_id"]] = note
            print(f"  {r['case_id']} [Vibe Audit] -> not healable by design")
            continue
        print(f"  healing {r['case_id']} ...", flush=True)
        note = heal_case(
            r["case_id"], r.get("suite", ""), r.get("error") or "",
            project, tests_dir, reports_dir, run_id,
        )
        healing_notes[r["case_id"]] = note or "UNHEALED"
        print(f"    -> {note.split(':')[0] if note else 'UNHEALED'}")

    # Independent verification: re-run the full suite and rebuild results,
    # carrying the healing notes for cases that now pass.
    ss = _session_state_path(project, args)
    rc, report = run_tests(project, tests_dir, reports_dir, run_id, storage_state=ss)
    from qax.excel_parser import parse_workbook

    wb = project / "test_cases.xlsx"
    cases = parse_workbook(wb) if wb.exists() else []
    results = build_results(run_id, git_commit(project), report, cases, healing_notes)
    save_results(results, results_path)
    s = results["summary"]
    print(f"\nafter heal: total={s['total']} passed={s['passed']} "
          f"failed={s['failed']} healed={s['healed']}")
    for r in results["results"]:
        if r.get("healed"):
            print(f"  HEALED {r['case_id']}: {r['healing_note'][:120]}")
    return 0 if s["failed"] == 0 else 1


def cmd_session(args: argparse.Namespace) -> int:
    """Open a headed browser for the USER to sign in; save the session."""
    from qax.runner import capture_session

    project = Path(args.project or os.getcwd()).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = project / out
    out.parent.mkdir(parents=True, exist_ok=True)
    url = args.app_url or _resolve_app_url(project, args, []) or "http://localhost:5173/auth"
    ok = capture_session(url, out, timeout_s=args.timeout)
    if not ok:
        print("session capture failed — see messages above", file=sys.stderr)
        return 1
    print(f"\nsession saved to {out}")
    print(f"next: qax run --workbook <wb> [--headed]   (auto-uses {out})")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    path = Path(args.file or (Path(args.project or os.getcwd()).resolve() / "automation" / "results.json"))
    if not path.exists():
        print(f"error: no results file at {path}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    print(f"run_id   : {data.get('run_id')}")
    print(f"commit   : {data.get('commit')}")
    print(f"timestamp: {data.get('timestamp')}")
    print(f"summary  : total={summary.get('total')} passed={summary.get('passed')} "
          f"failed={summary.get('failed')} skipped={summary.get('skipped')} healed={summary.get('healed')}")
    failed = [r for r in data.get("results", []) if r.get("status") == "failed"]
    if failed:
        print(f"\n{len(failed)} FAILED case(s):")
        for r in failed:
            print(f"  - {r.get('case_id')} [{r.get('suite')}] {r.get('error') or ''}")
            if r.get("healing_note"):
                print(f"      healed: {r['healing_note']}")
    return 1 if failed else 0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qax",
        description="QA test automation on an embedded agent core.",
    )
    p.add_argument("--version", action="version", version=f"qax {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="bootstrap the qax home (~/.qax)")
    sp.add_argument("--copy-env-from", action="store_true",
                    help="seed ~/.qax/.env from a previous install's .env (API keys)")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("doctor", help="health-check the qax environment")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("plan", help="phase-1: recon, suite check, 3 generation agents, human-in-the-loop")
    sp.add_argument("--project", default=None, help="project folder (default: cwd)")
    sp.add_argument("--continue", dest="continue_", action="store_true",
                    help="answer open questions interactively, then generate test cases")
    sp.add_argument("--answers", default=None,
                    help="path to answers.json (batch mode: {question_id: answer})")
    sp.add_argument("--app-url", default=None,
                    help="base URL for generated tests (default: auto-discovered local index.html)")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("run", help="regression: Excel test cases -> Playwright specs -> results.json")
    sp.add_argument("--workbook", default="test_cases.xlsx", help="path to the test-case workbook")
    sp.add_argument("--project", default=None, help="project folder (default: cwd)")
    sp.add_argument("--regenerate", action="store_true", help="rebuild spec files from the workbook")
    sp.add_argument("--headed", action="store_true",
                    help="run with a visible browser window (watch tests live)")
    sp.add_argument("--vibe-audit", action="store_true",
                    help="append the Vibe Audit suite: axe WCAG scan, contrast, headings, "
                         "focus, touch targets, emoji icons, reduced motion, mobile overflow, "
                         "theme census (workbook optional in this mode)")
    sp.add_argument("--app-url", default=None,
                    help="target URL for the vibe audit suite (default: state.json, then workbook)")
    sp.add_argument("--session-state", default=None,
                    help="Playwright storageState JSON with an authenticated session "
                         "(default: automation/session.json when present)")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("session", help="capture an authenticated session for later runs")
    sp.add_argument("--project", default=None, help="project folder (default: cwd)")
    sp.add_argument("--app-url", default=None, help="sign-in URL (default: state.json URL or localhost:5173/auth)")
    sp.add_argument("--out", default="automation/session.json", help="storageState output path")
    sp.add_argument("--timeout", type=int, default=300, help="seconds to wait for login (default 300)")
    sp.set_defaults(func=cmd_session)

    sp = sub.add_parser("heal", help="self-heal failed specs after a code update")
    sp.add_argument("--project", default=None, help="project folder (default: cwd)")
    sp.set_defaults(func=cmd_heal)

    sp = sub.add_parser("report", help="render automation/results.json as a summary")
    sp.add_argument("--file", default=None, help="path to results.json (default: <project>/automation/results.json)")
    sp.add_argument("--project", default=None, help="project folder (default: cwd)")
    sp.set_defaults(func=cmd_report)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
