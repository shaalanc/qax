"""Embedded agent core — the agent loop as a library.

Boot path mirrors the one-shot runner (``hermes_cli/oneshot.py::_run_agent``),
but returns ``(response, result)`` directly instead of printing to stdout.
Memory, skills, tools, delegation and session history all work — the same
machinery the CLI uses, pointed at the qax home.

NOTE: ``set_hermes_home_env()`` MUST run before any core module is imported.
It is called at import time here; import this module first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _sanitize_import_env() -> None:
    """Drop foreign PYTHONPATH/PYTHONHOME + sys.path entries (see qax.cli)."""
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

from qax.home import set_hermes_home_env

set_hermes_home_env()

# qax's tailored toolset — registered in toolsets.py under "qa".
DEFAULT_TOOLSETS = ["qa"]


def run(
    prompt: str,
    toolsets: Optional[list[str]] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, dict]:
    """Run one full agent turn against the embedded core.

    Returns ``(final_response_text, run_result_dict)``. Raises on agent
    construction/config errors; the caller decides how to surface them.
    """
    # Non-interactive posture — same env the one-shot runner sets.
    os.environ.setdefault("HERMES_YOLO_MODE", "1")
    os.environ.setdefault("HERMES_ACCEPT_HOOKS", "1")

    # Route delegate_task subagents to their synchronous path: nothing drains
    # the completion queue here, so without this every subagent result would
    # be discarded.
    try:
        from gateway.session_context import declare_stateless_channel

        declare_stateless_channel()
    except Exception:  # pragma: no cover - best effort
        pass

    from hermes_cli.oneshot import _run_agent

    return _run_agent(
        prompt,
        model=model,
        provider=provider,
        toolsets=list(toolsets or DEFAULT_TOOLSETS),
        use_config_toolsets=False,
    )
