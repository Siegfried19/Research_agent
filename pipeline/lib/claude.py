"""Headless Claude Code (`claude -p`) backend — runs scoring/summarizing without an
agent in the loop (billed to the user's Max subscription, no API key). Prompt goes
in via stdin; result comes from stdout.

To add a second model (e.g. Codex) for a cross-model review panel, copy this file
to lib/codex.py and swap the command (see MEMORY: cross-model-codex-panel).
"""
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
MODEL = os.environ.get("SUMMARY_MODEL", "opus")


def run_claude(prompt, model=None, timeout=300, tools=None):
    """Run one `claude -p` call. Returns trimmed stdout. Raises on non-zero/timeout.
    tools: optional list of tool names to allow (e.g. ["WebSearch", "WebFetch"]) —
    headless runs have no permission prompt, so anything not allowed is denied."""
    binp = shutil.which(CLAUDE_BIN)
    if not binp:
        raise RuntimeError(f"'{CLAUDE_BIN}' not found — install & log into Claude Code first.")
    cmd = [binp, "-p", "--model", model or MODEL]
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    proc = subprocess.run(
        cmd,
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p exit {proc.returncode}: {(proc.stderr or '').strip()[:300]}")
    return (proc.stdout or "").strip()


def pool(items, worker, limit=3):
    """Bounded-concurrency map: run worker(item, i) over items, <=limit at once.
    Returns results in order; an exception for an item becomes {'error': str}."""
    results = [None] * len(items)

    def run(idx_item):
        i, item = idx_item
        try:
            return i, worker(item, i)
        except Exception as e:  # noqa: BLE001
            return i, {"error": str(e)}

    with ThreadPoolExecutor(max_workers=max(1, min(limit, len(items) or 1))) as ex:
        for i, res in ex.map(run, list(enumerate(items))):
            results[i] = res
    return results
