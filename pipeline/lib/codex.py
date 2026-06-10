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
from pathlib import Path

from .claude import pool  # noqa: F401  (re-export: same bounded-concurrency pool)

CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_MODEL = os.environ.get("CODEX_MODEL")  # None = account default


def run_codex(prompt, model=None, timeout=300):
    """Run one `codex exec` call. Returns the final message text. Raises on failure.
    Uses --output-last-message so we get a clean answer (stdout mixes in session log)."""
    binp = shutil.which(CODEX_BIN)
    if not binp:
        raise RuntimeError(f"'{CODEX_BIN}' not found — npm i -g @openai/codex && codex login")
    out_file = Path(tempfile.gettempdir()) / f"codex_out_{os.getpid()}_{abs(hash(prompt)) % 10**8}.txt"
    cmd = [binp, "exec", "--skip-git-repo-check", "--output-last-message", str(out_file)]
    m = model or CODEX_MODEL
    if m:
        cmd += ["-m", m]
    cmd.append("-")  # read prompt from stdin
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              encoding="utf-8", timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"codex exec exit {proc.returncode}: {(proc.stderr or '').strip()[:300]}")
        if out_file.exists():
            return out_file.read_text(encoding="utf-8").strip()
        return (proc.stdout or "").strip()  # fallback: old codex without the flag
    finally:
        out_file.unlink(missing_ok=True)
