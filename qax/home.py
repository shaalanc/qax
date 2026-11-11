"""qax home-directory bootstrap.

qax is fully self-contained: all state lives under QAX_HOME (default
``~/.qax``), which the embedded agent core uses as its home directory
(``HERMES_HOME``). Set the environment variable BEFORE importing any core
module (``set_hermes_home_env`` is called at the top of ``qax.agent_core``
and ``qax.cli``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

QAX_HOME_ENV = "QAX_HOME"
DEFAULT_QAX_HOME = ".qax"

# Subdirectories the embedded core expects under its home.
_HOME_SUBDIRS = ("skills", "sessions", "logs", "memories")

# Snapshot the parent process's home env var BEFORE qax overrides it (import
# order guarantees this runs first via qax.cli). Used only to locate a
# pre-existing install's .env for --copy-env-from.
_PARENT_HERMES_HOME = os.environ.get("HERMES_HOME")


def qax_home() -> Path:
    env = os.environ.get(QAX_HOME_ENV)
    if env:
        return Path(env).expanduser()
    return Path.home() / DEFAULT_QAX_HOME


def set_hermes_home_env() -> None:
    """Force HERMES_HOME to the qax home.

    Deliberately an ASSIGNMENT, not setdefault: a parent process (a desktop
    app or a shell with another agent install) may export the home env var
    pointing at its own install. qax must NEVER write state (memory,
    sessions, skills, state.db) into another install.
    """
    os.environ["HERMES_HOME"] = str(qax_home())


def ensure_home() -> Path:
    """Create the qax home skeleton if missing; return its path."""
    home = qax_home()
    for sub in _HOME_SUBDIRS:
        (home / sub).mkdir(parents=True, exist_ok=True)
    return home


def install_default_config(home: Path | None = None) -> Path:
    """Copy the fork's example config.yaml into the qax home on first run."""
    home = home or qax_home()
    cfg = home / "config.yaml"
    if cfg.exists():
        return cfg
    example = Path(__file__).resolve().parent.parent / "cli-config.yaml.example"
    if example.exists():
        shutil.copyfile(example, cfg)
    else:
        cfg.write_text(
            "# qax minimal config\nmodel:\n  provider: deepseek\n  default: deepseek-chat\n",
            encoding="utf-8",
        )
    return cfg


def env_file(home: Path | None = None) -> Path:
    return (home or qax_home()) / ".env"


def _has_real_keys(env: Path) -> bool:
    """True if the file contains at least one non-comment KEY=value line."""
    try:
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if key.strip() and val.strip():
                    return True
    except Exception:
        return False
    return False


def _hermes_env_candidates() -> list[Path]:
    """Where a previous install might keep its .env (secrets)."""
    cands: list[Path] = []
    if _PARENT_HERMES_HOME:
        p = Path(_PARENT_HERMES_HOME).expanduser()
        if p != qax_home():
            cands.append(p / ".env")
    cands.append(Path.home() / ".hermes" / ".env")
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            cands.append(Path(local) / "hermes" / ".env")
    seen: set[str] = set()
    uniq: list[Path] = []
    for c in cands:
        s = str(c)
        if s not in seen:
            seen.add(s)
            uniq.append(c)
    return uniq


def ensure_env(home: Path | None = None, copy_from_hermes: bool = False) -> Path:
    """Create ~/.qax/.env with commented placeholders, or optionally seed it
    from a previous install's .env so API keys carry over.

    The copy overwrites the placeholder template: a placeholder .env has no
    real keys, so there is nothing to preserve.
    """
    home = home or qax_home()
    env = env_file(home)
    if copy_from_hermes:
        for cand in _hermes_env_candidates():
            if cand.exists() and (not env.exists() or not _has_real_keys(env)):
                shutil.copyfile(cand, env)
                # The OAuth/credential pool (OpenRouter/Nous tokens) lives in
                # auth.json next to the .env; provider resolution needs it.
                auth_src = cand.parent / "auth.json"
                auth_dst = home / "auth.json"
                if auth_src.exists() and not auth_dst.exists():
                    shutil.copyfile(auth_src, auth_dst)
                return env
    if env.exists():
        return env
    env.write_text(
        "# qax secrets — API keys only (settings live in config.yaml)\n"
        "# Uncomment and fill in your provider key:\n"
        "# DEEPSEEK_API_KEY=sk-...\n"
        "# OPENAI_API_KEY=sk-...\n",
        encoding="utf-8",
    )
    return env


def _hermes_config_candidates() -> list[Path]:
    """Where a previous install keeps config.yaml (settings)."""
    return [c.parent / "config.yaml" for c in _hermes_env_candidates()]


def mirror_hermes_model_config(home: Path | None = None) -> bool:
    """Copy ``model.default``/``model.provider`` from a discovered
    previous config into the qax config, so the embedded agent uses the
    same provider the user already configured (avoids example-config
    fallbacks that 404).

    Returns True when a previous config was found and mirrored.
    """
    cfg = (home or qax_home()) / "config.yaml"
    if not cfg.exists():
        return False
    import yaml

    for cand in _hermes_config_candidates():
        if not cand.exists():
            continue
        try:
            with open(cand, encoding="utf-8") as f:
                hermes_cfg = yaml.safe_load(f) or {}
            m = hermes_cfg.get("model") or {}
            if not isinstance(m, dict):
                continue
            default = m.get("default") or m.get("model")
            provider = m.get("provider")
            base_url = m.get("base_url")
            if not (default or provider):
                continue
            from ruamel.yaml import YAML

            y = YAML()
            with open(cfg, encoding="utf-8") as f:
                d = y.load(f)
            d.setdefault("model", {})
            if default:
                d["model"]["default"] = default
            if provider:
                d["model"]["provider"] = provider
            if base_url is not None:
                # CRITICAL: the example config ships model.base_url pointing at
                # OpenRouter, which overrides the provider registry default and
                # sends every request to the wrong endpoint. Mirror the previous
                # value (usually '' -> registry default) verbatim.
                d["model"]["base_url"] = str(base_url).strip()
            with open(cfg, "w", encoding="utf-8") as f:
                y.dump(d, f)
            return True
        except Exception:
            continue
    return False


# --------------------------------------------------------------------------- #
# Node.js / Playwright runtime (JS specs)
# --------------------------------------------------------------------------- #
_NODE_PKG = {
    "name": "qax-node-runtime",
    "private": True,
    "dependencies": {
        "@playwright/test": "^1.49.0",
        "axe-core": "^4.10.0",
    },
}


def node_bin() -> str | None:
    """Path to a usable node.exe (PATH first, then Program Files)."""
    exe = shutil.which("node")
    if exe:
        return exe
    roots = [
        os.environ.get("ProgramFiles", "C:/Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"),
    ]
    for root in roots:
        cand = Path(root) / "nodejs" / "node.exe"
        if cand.exists():
            return str(cand)
    return None


def node_runtime_dir(home: Path | None = None) -> Path:
    """Where qax keeps its Node toolchain (@playwright/test install)."""
    return (home or qax_home()) / "node"


def playwright_cli_path(home: Path | None = None) -> Path:
    return node_runtime_dir(home) / "node_modules" / "@playwright" / "test" / "cli.js"


def ensure_node_runtime(home: Path | None = None, install_browsers: bool = True) -> tuple[str, str]:
    """Provision the JS runner: node.exe + @playwright/test + Chromium.

    One-time cost (npm install + browser download) lands under
    ``~/.qax/node``. Returns ``(node_exe, playwright_cli_js)``. Raises
    RuntimeError with a fix hint when Node is missing or the install fails.
    """
    home = home or qax_home()
    node = node_bin()
    if not node:
        raise RuntimeError(
            "Node.js not found — install the LTS from https://nodejs.org, "
            "then re-run `qax init`."
        )
    nd = node_runtime_dir(home)
    nd.mkdir(parents=True, exist_ok=True)
    pkg = nd / "package.json"
    # Always (re)write the manifest from _NODE_PKG so dep additions (e.g.
    # axe-core) reach existing installs; npm install only runs when a
    # declared module is missing.
    pkg.write_text(json.dumps(_NODE_PKG, indent=2), encoding="utf-8")
    cli = playwright_cli_path(home)
    axe = nd / "node_modules" / "axe-core" / "axe.js"
    if not cli.exists() or not axe.exists():
        print("installing @playwright/test into ~/.qax/node (one-time) ...", flush=True)
        npm = "npm.cmd" if os.name == "nt" else "npm"
        subprocess.run(
            [npm, "install", "--prefix", str(nd), "--no-audit", "--no-fund"],
            timeout=600,
        )
        if not cli.exists():
            raise RuntimeError(
                "npm install of @playwright/test failed — check your network/npm, "
                "then re-run `qax init`."
            )
    if install_browsers:
        print("checking Playwright Chromium browser ...", flush=True)
        subprocess.run([node, str(cli), "install", "chromium"], timeout=900)
    if not cli.exists():
        raise RuntimeError(
            "npm install of @playwright/test failed — check your network/npm, "
            "then re-run `qax init`."
        )
    if not axe.exists():
        raise RuntimeError(
            "npm install of axe-core failed — check your network/npm, "
            "then re-run `qax init`."
        )
    return node, str(cli)
