"""Execute the generated Playwright (JS) specs and capture results.

The Node runtime and ``@playwright/test`` are provisioned once under the qax
home (~/.qax/node); the per-project ``automation/tests`` folder links to that
install so the specs can ``require('@playwright/test')`` with no project-level
npm setup.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from qax.home import ensure_node_runtime, node_runtime_dir


def git_commit(project: Path) -> str:
    """HEAD commit SHA of the project under test ("" when not a git repo)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def _ensure_node_modules_link(tests_dir: Path) -> None:
    """Link tests_dir/node_modules to the qax-home node install so spec
    files can ``require('@playwright/test')`` without project npm setup."""
    link = tests_dir / "node_modules"
    if link.exists() or link.is_symlink():
        return
    nm = node_runtime_dir() / "node_modules"
    try:
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(nm)],
                capture_output=True, check=True, timeout=30,
            )
        else:
            os.symlink(nm, link, target_is_directory=True)
    except Exception:
        pass  # NODE_PATH is also set on the run command as a fallback


def _write_config(reports_dir: Path, run_id: str, tests_dir: Path, headed: bool,
                  storage_state: str | None = None) -> Path:
    """Write the per-run Playwright config (absolute paths, JSON reporter)."""
    artifacts = reports_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    use: dict = {
        "headless": not headed,
        "screenshot": "only-on-failure",
        "video": "off",
        "trace": "off",
    }
    if storage_state:
        use["storageState"] = str(Path(storage_state).resolve()).replace("\\", "/")
    cfg = {
        "testDir": str(tests_dir).replace("\\", "/"),
        "outputDir": str(artifacts).replace("\\", "/"),
        "timeout": 120000,
        "workers": 1,
        "retries": 0,
        "use": use,
        "reporter": [
            ["json", {"outputFile": str(reports_dir / f"{run_id}.json").replace("\\", "/")}],
            ["line"],
        ],
    }
    path = reports_dir / "playwright.config.js"
    path.write_text(
        "// qax-generated Playwright config (run " + run_id + ")\n"
        "module.exports = " + json.dumps(cfg, indent=2) + ";\n",
        encoding="utf-8",
    )
    return path


def _run(node: str, cli: str, config: Path, reports_dir: Path, run_id: str,
         grep: str | None = None, extra_args: list[str] | None = None) -> int:
    env = dict(os.environ)
    env["NODE_PATH"] = str(node_runtime_dir() / "node_modules")
    cmd = [node, cli, "test", "--config", str(config)]
    if grep:
        # CLI --grep (regex on the full test title) — the config-file `grep`
        # option requires a RegExp object and rejects strings.
        cmd.extend(["--grep", grep])
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
    log = reports_dir / f"{run_id}.log"
    log.write_text(proc.stdout + "\n---STDERR---\n" + proc.stderr, encoding="utf-8")
    return proc.returncode


def run_tests(project: Path, tests_dir: Path, reports_dir: Path, run_id: str,
              extra_args: list[str] | None = None, headed: bool = False,
              storage_state: str | None = None) -> tuple[int, Path]:
    """Run the Playwright (JS) suite over tests_dir.

    Returns ``(exit_code, json_report_path)``. Screenshots land under
    ``reports_dir/artifacts/``; console output is saved to
    ``reports_dir/<run_id>.log``. ``headed=True`` shows a visible browser.
    ``storage_state`` (optional) is a Playwright storageState JSON — the
    session captured by ``qax session`` for authenticated suites.
    """
    node, cli = ensure_node_runtime()
    _ensure_node_modules_link(tests_dir)
    config = _write_config(reports_dir, run_id, tests_dir, headed, storage_state)
    rc = _run(node, cli, config, reports_dir, run_id, extra_args=extra_args)
    return rc, reports_dir / f"{run_id}.json"


def run_single_test(tests_dir: Path, test_grep: str, project: Path,
                    reports_dir: Path, run_id: str) -> int:
    """Re-run one case (grep by case id) — used by the healer to verify fixes."""
    node, cli = ensure_node_runtime()
    _ensure_node_modules_link(tests_dir)
    config = _write_config(reports_dir, run_id, tests_dir, headed=False)
    return _run(node, cli, config, reports_dir, run_id, grep=test_grep)


def single_test_command(tests_dir: Path, test_grep: str, reports_dir: Path, run_id: str) -> str:
    """Exact shell command for the healer agent to re-run one case."""
    node, cli = ensure_node_runtime()
    _ensure_node_modules_link(tests_dir)
    config = _write_config(reports_dir, run_id, tests_dir, headed=False)
    return f'"{node}" "{cli}" test --config "{config}" --grep "{test_grep}"'


# --------------------------------------------------------------------------- #
# Session capture (authenticated suites)
# --------------------------------------------------------------------------- #
_SESSION_SCRIPT = r"""
const { chromium } = require('playwright');
const url = process.argv[2];
const out = process.argv[3];
const timeoutMs = parseInt(process.argv[4] || '300000', 10);
(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  console.log('SIGN IN TO ' + url + ' IN THE OPENED WINDOW, THEN WAIT.');
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const deadline = Date.now() + timeoutMs;
  let authed = false;
  while (Date.now() < deadline) {
    await page.waitForTimeout(2000);
    try {
      const st = await page.evaluate(() => {
        return { p: location.pathname, hasSession: document.cookie.length > 0 || !location.pathname.toLowerCase().includes('auth') };
      });
      if (st.hasSession && !st.p.toLowerCase().includes('auth')) { authed = true; break; }
    } catch (e) { /* page navigating */ }
  }
  if (!authed) { console.error('TIMEOUT: no session detected after ' + Math.round(timeoutMs / 1000) + 's'); await browser.close(); process.exit(2); }
  await context.storageState({ path: out });
  await browser.close();
  console.log('SESSION SAVED -> ' + out);
})().catch(e => { console.error('SESSION FAILED: ' + (e && e.message)); process.exit(1); });
"""


def capture_session(app_url: str, out_path: Path, timeout_s: int = 300) -> bool:
    """Open a headed browser, let the USER sign in, then save storageState.

    Returns True when a session was captured (user completed login).
    """
    node, _cli = ensure_node_runtime()
    script = node_runtime_dir() / "session-capture.js"
    script.write_text(_SESSION_SCRIPT, encoding="utf-8")
    env = dict(os.environ)
    env["NODE_PATH"] = str(node_runtime_dir() / "node_modules")
    print(f"session capture: sign in to {app_url} in the browser window that just opened")
    print(f"(waiting up to {timeout_s}s for you to complete login ...)")
    proc = subprocess.run(
        [node, str(script), app_url, str(out_path.resolve()), str(timeout_s * 1000)],
        capture_output=True, text=True, timeout=timeout_s + 60, env=env,
    )
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode == 0 and out_path.exists()
