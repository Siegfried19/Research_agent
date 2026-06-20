"""Automated versioned summary update: one `claude -p` per paper (replaces the old
update.workflow agent). Reads store/update_worklist.json, inlines the current
summary + related summaries, writes a new version vN+1. Idempotent (skips existing).
Usage: python3 pipeline/tools/update_auto.py [concurrency]
"""
import json
import sys
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log

log = get_logger("update")


def prompt(w, current_md, related_blocks):
    rels = "\n\n".join(related_blocks)
    return f"""你在做论文总结的"版本化更新"。基于下面给出的内容,为论文写一份**新版中文总结**。

保持原有结构与三段置顶模板(一句话/解决了什么问题/用什么方法解决的/动机/方法细节/数据集/结果/核心贡献/局限与我的质疑),但要:
- **整合相关工作的视角**: 这篇论文在更广文献脉络中的位置、被后续工作如何延展/挑战/超越、其方法或结论在新证据下是否仍站得住。
- 新增一节 `## 在相关工作脉络中的更新` —— 简述本次更新(v{w['nextVersion']})参考了哪些相关论文及其带来的新认识。
- 保留并深化"局限与我的质疑"。
- frontmatter: version: {w['nextVersion']},based_on: {json.dumps([r['id'] for r in w['related']], ensure_ascii=False)},note: 一句话说明本次更新依据。

**直接输出新版 markdown 本身**,不要额外说明、不要代码围栏。不要臆造。

==== 当前版本总结 ====
{current_md}

==== 相关论文的总结 ====
{rels}"""


def main():
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    wl = ROOT / "storage" / "update_worklist.json"
    if not wl.exists():
        print("no update_worklist.json (run prepare_update.py first)", file=sys.stderr)
        sys.exit(1)
    work = json.loads(wl.read_text(encoding="utf-8"))["work"]
    todo = [w for w in work if not Path(w["outPath"]).exists()]
    log.info(f"update_auto: {len(work)} in worklist, {len(todo)} to do, concurrency={concurrency}")

    def worker(w, _i):
        current_md = Path(w["currentPath"]).read_text(encoding="utf-8", errors="ignore")
        blocks = []
        for r in w["related"]:
            try:
                blocks.append(f"### {r.get('title') or r['id']}\n" + Path(r["path"]).read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        md = run_claude(prompt(w, current_md, blocks))
        if not md or len(md) < 200:
            raise RuntimeError(f"bad output ({len(md)} chars)")
        Path(w["outPath"]).parent.mkdir(parents=True, exist_ok=True)
        Path(w["outPath"]).write_text(md, encoding="utf-8")
        log.info(f"  OK v{w['nextVersion']} {(w.get('title') or '')[:45]}")
        return {"ok": True}

    res = pool(todo, worker, concurrency)
    ok = sum(1 for r in res if isinstance(r, dict) and r.get("ok"))
    log.info(f"update_auto done: {ok}/{len(todo)} (then run register_updates.py)")
    run_log("-", f"update_auto: {ok}/{len(todo)} updated")


if __name__ == "__main__":
    main()
