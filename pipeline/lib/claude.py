"""Headless Claude Code (`claude -p`) backend — runs scoring/summarizing without an
agent in the loop (billed to the user's Max subscription, no API key). Prompt goes
in via stdin; result comes from stdout.

To add a second model (e.g. Codex) for a cross-model review panel, copy this file
to lib/codex.py and swap the command (see MEMORY: cross-model-codex-panel).
"""
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
MODEL = os.environ.get("SUMMARY_MODEL", "opus")
# 用量探针(2026-06-17,可逆):LLM_USAGE_LOG 指向一个 JSONL 文件时,改用 `--output-format json`
# 取回 token/cost,逐次 append 一行。默认 unset → 行为与从前一字不差(纯文本 stdout)。
USAGE_LOG = os.environ.get("LLM_USAGE_LOG")


def _log_usage(engine, rec):
    try:
        with open(USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"engine": engine, **rec}, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001  探针绝不阻断主流程
        pass


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
    if USAGE_LOG:
        cmd += ["--output-format", "json"]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # 超时归一成可分类的错(同 codex:不让裸 TimeoutExpired 漏出,否则失败分类层认不出)。
        raise RuntimeError(f"claude -p timed out after {timeout}s (no response)")
    if proc.returncode != 0:
        # 保留 stderr 尾部 2000 字(原 300 太短,Max 限流横幅可能被切掉 → 分类器看不到证据)。
        raise RuntimeError(f"claude -p exit {proc.returncode}: {(proc.stderr or '').strip()[-2000:]}")
    out = (proc.stdout or "").strip()
    if USAGE_LOG:
        try:
            obj = json.loads(out)
            u = obj.get("usage") or {}
            _log_usage("claude", {
                "wall_s": round(time.time() - t0, 1),
                "duration_ms": obj.get("duration_ms"),
                "num_turns": obj.get("num_turns"),
                "input_tokens": u.get("input_tokens"),
                "output_tokens": u.get("output_tokens"),
                "cache_creation_input_tokens": u.get("cache_creation_input_tokens"),
                "cache_read_input_tokens": u.get("cache_read_input_tokens"),
                "total_cost_usd": obj.get("total_cost_usd"),
            })
            return (obj.get("result") or "").strip()
        except Exception:  # noqa: BLE001  json 解析失败就退回原始 stdout,不丢结果
            return out
    return out


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
