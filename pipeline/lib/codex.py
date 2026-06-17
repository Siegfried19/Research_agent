"""Headless OpenAI Codex CLI (`codex exec`) backend — the second model of the
cross-model review panel (billed to the user's ChatGPT subscription, no API key).
Mirror of lib/claude.py: prompt via stdin, result via stdout.

Used for: devil's-advocate seat in scoring (score_auto), summary fact-checking
(verify_summaries). Codex never has veto power — it only objects / reports.
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .claude import pool, _log_usage, USAGE_LOG  # noqa: F401  (re-export pool; reuse usage probe)

CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_MODEL = os.environ.get("CODEX_MODEL")  # None = account default


def run_codex(prompt, model=None, timeout=300, images=None, sandbox=None, cwd=None):
    """Run one `codex exec` call. Returns the final message text. Raises on failure.
    Uses --output-last-message so we get a clean answer (stdout mixes in session log).
    images:  optional list of image file paths attached via `-i` (e.g. page PNGs).
    sandbox: 'read-only' | 'workspace-write' | 'danger-full-access'. workspace-write
             lets the agent run code (e.g. render a PDF page to PNG and *look* at it).
    cwd:     working root (`-C`); point it at a throwaway dir so the agent's scratch
             files stay contained and get cleaned up by the caller."""
    binp = shutil.which(CODEX_BIN)
    if not binp:
        raise RuntimeError(f"'{CODEX_BIN}' not found — npm i -g @openai/codex && codex login")
    out_file = Path(tempfile.gettempdir()) / f"codex_out_{os.getpid()}_{abs(hash(prompt)) % 10**8}.txt"
    cmd = [binp, "exec", "--skip-git-repo-check", "--output-last-message", str(out_file)]
    m = model or CODEX_MODEL
    if m:
        cmd += ["-m", m]
    if sandbox:
        cmd += ["--sandbox", sandbox]
    if cwd:
        cmd += ["-C", cwd]
    for img in (images or []):
        cmd += ["-i", img]
    cmd.append("-")  # read prompt from stdin
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              encoding="utf-8", timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"codex exec exit {proc.returncode}: {(proc.stderr or '').strip()[:300]}")
        if out_file.exists():
            return out_file.read_text(encoding="utf-8").strip()
        return (proc.stdout or "").strip()  # fallback: old codex without the flag
    finally:
        if USAGE_LOG:
            # codex 不经 --output-last-message 暴露 token,这里只记时长(配额是 ChatGPT 侧,
            # 主要关心 claude 的 token;codex 时长用于估全量核查耗时)。
            _log_usage("codex", {"wall_s": round(time.time() - t0, 1)})
        out_file.unlink(missing_ok=True)
