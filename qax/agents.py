"""Phase-1 generation agents (used when a project has NO test suites).

Three parallel background agents analyse the project — business
requirements / user stories / unit tests. Each writes a Markdown document
plus its open questions (STRICT no-assumptions rule). The questions merge
into ``automation/questions.json`` for the human-in-the-loop phase; after
answers, parallel per-story agents generate test cases that merge into
``test_cases.xlsx`` — the input of ``qax run``.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from qax.agent_core import run as agent_run

ARTIFACTS_DIR = "artifacts"
QUESTIONS_FILE = "questions.json"
ANSWERS_FILE = "answers.json"

_GEN_RULES = (
    "STRICT RULES:\n"
    "- NEVER assume anything about the project. Every ambiguity, unknown, or "
    "undocumented decision becomes an Open Question.\n"
    "- Do NOT use the clarify tool. Do NOT try to ask the user interactively.\n"
    "- Do NOT modify any project files except the two output files.\n"
    "- If the project has no code or is ambiguous, say so honestly in the "
    "document and convert the intent questions into Open Questions."
)

_REQ_PROMPT = """You are qax's Business Requirements analyst agent.

Project: {project}
Recon context (may be sparse):
{recon}

Task: produce a Business Requirements document.
1. Inspect the project (source, docs, manifests). Extract functional and
   non-functional requirements. If the project is empty, document that and
   focus questions on intent.
2. Write {out_md} as Markdown with sections:
   ## Overview / ## Functional Requirements (FR-1..n: description + priority)
   ## Non-Functional Requirements (NFR-1..n) / ## Open Questions
3. Write {out_questions} as a JSON array of objects:
   [{{"id": "br-1", "question": "...", "why": "what the answer unlocks"}}]

{GEN_RULES}"""

_STORY_PROMPT = """You are qax's User Stories analyst agent.

Project: {project}
Recon context (may be sparse):
{recon}

Task: derive user stories from the project (and any business requirements).
1. Inspect the project. Write user stories in the form:
   "As a <role>, I want <capability>, so that <benefit>", each with 2-4
   Given/When/Then acceptance criteria and a story id (US-001...).
2. Write {out_md} as Markdown: ## Overview / ## User Stories / ## Open Questions
3. Write {out_questions} as a JSON array: [{{"id": "us-1", "question": "...", "why": "..."}}]
4. ALSO write {out_json} as a JSON array (machine-readable, for downstream
   generation): [{{"story_id": "US-001", "title": "...", "acceptance_criteria": ["..."]}}]

{GEN_RULES}"""

_UNIT_PROMPT = """You are qax's Unit Test analyst agent.

Project: {project}
Recon context (may be sparse):
{recon}

Task: analyse the project for unit-level testability.
1. Inspect the code. Identify the modules/functions with the highest test
   value, the test framework that fits the stack, and the file layout a
   unit-test suite should follow.
2. Write {out_md} as Markdown: ## Overview / ## Test Targets (module ->
   what to test) / ## Suggested Framework & Layout / ## Open Questions
3. Write {out_questions} as a JSON array: [{{"id": "ut-1", "question": "...", "why": "..."}}]

{GEN_RULES}"""


def _run_generation_agent(
    name: str,
    label: str,
    template: str,
    project: Path,
    artifacts: Path,
    recon: str,
) -> tuple[str, Path, Path]:
    out_md = artifacts / f"{name}.md"
    out_questions = artifacts / f"{name}.questions.json"
    out_json = artifacts / f"{name}.json" if name == "user_stories" else None
    prompt = template.format(
        project=project,
        recon=recon[:2500],
        out_md=out_md,
        out_questions=out_questions,
        out_json=out_json if out_json else "",
        GEN_RULES=_GEN_RULES,
    )
    response, _result = agent_run(prompt, toolsets=["qa"])
    return name, out_md, out_questions


def run_generation_agents(project: Path, recon_md: Path | None = None) -> Path:
    """Spawn the 3 parallel generation agents.

    Returns the merged ``automation/questions.json`` path. Raises on agent
    failure (the caller surfaces it).
    """
    artifacts = project / "automation" / ARTIFACTS_DIR
    artifacts.mkdir(parents=True, exist_ok=True)
    recon = ""
    if recon_md and recon_md.exists():
        recon = recon_md.read_text(encoding="utf-8")

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(_run_generation_agent, name, label, tpl, project, artifacts, recon): name
            for name, label, tpl in (
                ("requirements", "Business Requirements", _REQ_PROMPT),
                ("user_stories", "User Stories", _STORY_PROMPT),
                ("unit_tests", "Unit Tests", _UNIT_PROMPT),
            )
        }
        for fut in as_completed(futures):
            name = futures[fut]
            fut.result()  # re-raise on failure
            print(f"  done: {name}")

    questions = _merge_questions(artifacts)
    qpath = project / "automation" / QUESTIONS_FILE
    qpath.write_text(json.dumps(questions, indent=2), encoding="utf-8")
    return qpath


def _merge_questions(artifacts: Path) -> list[dict]:
    merged: list[dict] = []
    for name in ("requirements", "user_stories", "unit_tests"):
        f = artifacts / f"{name}.questions.json"
        if not f.exists():
            continue
        try:
            qs = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            qs = []
        for i, q in enumerate(qs, 1):
            if isinstance(q, dict) and q.get("question"):
                merged.append(
                    {
                        "id": q.get("id") or f"{name[:2]}-{i}",
                        "question": q["question"],
                        "why": q.get("why", ""),
                        "source": name,
                    }
                )
    return merged


def interactive_answers(questions: list[dict], answers_path: Path) -> dict:
    """Ask each question via stdin. Returns {id: answer}. Raises EOFError
    when stdin is not interactive."""
    answers: dict[str, str] = {}
    for q in questions:
        print(f"\n[{q['id']}] ({q['source']}) {q['question']}")
        if q.get("why"):
            print(f"    why: {q['why']}")
        answers[q["id"]] = input("> ").strip()
    answers_path.write_text(json.dumps(answers, indent=2), encoding="utf-8")
    return answers


def load_answers(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"answers file must be a JSON object of {{id: answer}}: {path}")
    return data


def apply_answers(project: Path, answers: dict, questions: list[dict]) -> None:
    """Append an Answers section to each generation .md that has answers."""
    by_id = {q["id"]: q for q in questions}
    artifacts = project / "automation" / ARTIFACTS_DIR
    for name in ("requirements", "user_stories", "unit_tests"):
        md = artifacts / f"{name}.md"
        if not md.exists():
            continue
        relevant = [q for qid, q in by_id.items() if q["source"] == name and qid in answers]
        if not relevant:
            continue
        section = "\n\n## Answers (human-in-the-loop)\n"
        for q in relevant:
            section += f"- **{q['id']}** {q['question']}\n  → {answers[q['id']]}\n"
        with md.open("a", encoding="utf-8") as f:
            f.write(section)
        print(f"  updated: {md.name}")


def _find_app_url(project: Path) -> str:
    """Best-effort entry URL for generated tests (file:// of the app HTML)."""
    candidates = [
        project / "index.html",
        project / "app" / "index.html",
        project / "src" / "index.html",
        project / "public" / "index.html",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve().as_uri()
    for f in sorted(project.rglob("index.html")):
        return f.resolve().as_uri()
    return "http://localhost:8000"


def run_story_case_agents(project: Path, answers: dict, app_url: str | None = None) -> Path:
    """Spawn one test-case designer agent per user story; merge their case
    rows into test_cases.xlsx (the qax run input)."""
    artifacts = project / "automation" / ARTIFACTS_DIR
    stories_path = artifacts / "user_stories.json"
    if not stories_path.exists():
        raise FileNotFoundError(
            f"missing {stories_path} — the user-stories agent did not produce "
            "structured stories; re-run `qax plan`"
        )
    stories = json.loads(stories_path.read_text(encoding="utf-8"))
    if not stories:
        raise ValueError("user_stories.json is empty — nothing to generate cases for")

    out_dir = artifacts / "cases"
    out_dir.mkdir(parents=True, exist_ok=True)
    app_url = app_url or _find_app_url(project)

    def _one(story: dict) -> str:
        story_id = story.get("story_id", "US-001")
        out = out_dir / f"cases_{story_id}.json"
        prompt = _CASE_PROMPT.format(
            story_id=story_id,
            title=story.get("title", ""),
            story_json=json.dumps(story, indent=2),
            out=out,
            app_url=app_url,
        )
        agent_run(prompt, toolsets=["qa"])
        return story_id

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(_one, s) for s in stories]
        for fut in as_completed(futures):
            print(f"  done: cases for {fut.result()}")

    return merge_case_files(out_dir, project / "test_cases.xlsx", app_url=app_url)


_CASE_PROMPT = """You are qax's test-case designer for story {story_id} ({title}).

Story (with acceptance criteria):
{story_json}

The app under test is served at this URL (use it verbatim in Open steps):
{app_url}

Design test cases covering: happy path, negative cases, edge cases, and any
data-driven variants. Write {out} as a JSON array of rows:

[{{"case_id": "US-001-1", "suite": "<story slug>", "title": "...",
   "steps": ["Open {app_url}", "Fill Username with admin", ...],
   "expected_result": "...", "severity": "critical|high|medium|low",
   "priority": "high|medium|low"}}]

Rules:
- case_id: "{story_id}-<n>".
- The app under test is ONLY reachable at {app_url}. NEVER use file:// or
  local disk paths in steps — every Open step uses {app_url}.
- Test-case discipline (qa-rules methodology):
  * Cover the happy path PLUS negative, boundary/edge, and state variants
    (repeat, stale, cancelled, expired) per story where they apply.
  * Security/authorization probes (direct URL access, altered inputs) come
    first — P0/P1 cases before cosmetic ones.
  * Expected results MUST be observable and precise: exact message, value,
    or page state — never "works correctly" or "should work".
  * NEVER invent business rules. If a rule is unclear, mark it explicitly
    as "(assumption)" in the title and keep the case to what is known.
- steps: natural-language action lines that qax's step grammar understands:
  open/go to <url>, click <target>, fill <target> with <value>,
  select <value> from <target>, check/uncheck <target>, wait for <target>,
  expect <text> is visible, expect url contains <x>, screenshot, wait <n>.
  Any step outside the grammar degrades to a TODO — prefer grammar steps.
- Do NOT modify any file except {out}. Do NOT use clarify."""


def merge_case_files(out_dir: Path, workbook_path: Path, app_url: str | None = None) -> Path:
    """Merge per-story case JSONs into an Excel workbook (qax run input).

    Substitutes ``<url>``/``[url]``/bare ``URL`` step placeholders with the
    discovered app URL — generation agents cannot reliably guess file://
    paths, so the orchestrator pins them at merge time.
    """
    from openpyxl import Workbook

    if app_url is None:
        app_url = _find_app_url(workbook_path.parent)

    def _sub(step: str) -> str:
        # Agents may write "Open <url>", "go to [url]", "URL" — replace every
        # placeholder token with the pinned app URL, wherever it appears.
        step = (
            step.replace("<url>", app_url)
            .replace("[url]", app_url)
            .replace("URL", app_url)
        )
        # Enforcement: with a live app_url, NEVER keep local file:// targets
        # (agents routinely fall back to paths they saw in the codebase).
        if app_url and not app_url.startswith("file:"):
            step = re.sub(r"file://[^\s\"'`)]*", app_url, step)
        return step

    rows: list[dict] = []
    for f in sorted(out_dir.glob("cases_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, list):
            rows.extend(r for r in data if isinstance(r, dict))

    wb = Workbook()
    ws = wb.active
    ws.title = "test_cases"
    ws.append(["case_id", "suite", "title", "steps", "expected_result", "severity", "priority"])
    for r in rows:
        steps = r.get("steps") or []
        if isinstance(steps, list):
            steps = "\n".join(f"{i+1}. {_sub(s)}" for i, s in enumerate(steps))
        ws.append(
            [
                r.get("case_id", ""),
                r.get("suite", ""),
                r.get("title", ""),
                steps,
                r.get("expected_result", ""),
                r.get("severity", "normal"),
                r.get("priority", "medium"),
            ]
        )
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(workbook_path)
    return workbook_path
