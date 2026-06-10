"""Rewrite summaries that failed cross-model fact-check (verify_summaries.py).
Unlike update_auto (integrates related work, no full text), this re-reads the
PAPER FULL TEXT plus the confirmed issues and produces a corrected version vN+1.
Input: store/correction_worklist.json  {"work":[{"paperId":..,"issues":[{quote,problem,severity}]}]}
Usage: python3 pipeline/correct_summaries.py [concurrency]
"""
import json
import sys
from datetime import date
from pathlib import Path

from lib.db import open_db, ROOT, now_iso
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log
from summarize_auto import full_text

MAX_CHARS = 120000
log = get_logger("correct")


def cprompt(title, current_md, issues, next_version, paper_id, text):
    issue_lines = "\n".join(
        f"- [{i.get('severity','?')}] 总结原句:“{i.get('quote','')}” — 问题:{i.get('problem','')}"
        for i in issues)
    return f"""你是论文精读员。下面给出:论文全文、这篇论文的当前中文总结、以及独立事实核查员(另一个模型对照原文)发现的错误清单。
请输出一份**修正版总结**。

要求:
- **逐条修正错误清单里的问题**:数字、方向、论断强度都以论文原文为准;被夸大的表述收敛到原文实际支持的程度。
- 错误清单之外的内容**尽量原样保留**(不要无端改写没问题的段落),但凡涉及具体数字/结论的句子,顺手对照原文再核一遍。
- 总结者自己的评注(领域地位、与研究主题的契合度、对后续工作的影响等)允许保留,但必须放在"局限与我的质疑"或明确以"(总结者注)"标出,**不得写成论文自身的论断**。
- 保持原有 markdown 结构与三段置顶模板,全文中文。
- **直接输出修正后的 markdown 本身**,不要任何额外说明、不要代码围栏。
- frontmatter 改为:
---
paper_id: {paper_id}
version: {next_version}
based_on: []
created_at: {date.today().isoformat()}
note: 事实核查修正(Codex 抽检发现 {len(issues)} 处问题)
---

==== 核查员发现的错误清单 ====
{issue_lines}

==== 当前版本总结 ====
{current_md}

==== 论文全文 ====
{text}"""


def run_corrections(work, concurrency=2):
    """work: [{"paperId":.., "issues":[{quote,problem,severity}]}]. Rewrites each
    summary as vN+1 (claude -p, full text + issue list), registers in DB.
    Returns the list of corrected entries. Idempotent (skips existing vN+1)."""
    conn = open_db()
    todo = []
    for w in work:
        p = conn.execute("SELECT id, slug, title, text_path, pdf_path FROM papers WHERE id=?",
                         (w["paperId"],)).fetchone()
        if not p:
            log.info(f"skip (not in db): {w['paperId']}")
            continue
        cur = conn.execute(
            "SELECT version, path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1",
            (w["paperId"],)).fetchone()
        if not cur:
            log.info(f"skip (no summary): {w['paperId']}")
            continue
        nv = cur["version"] + 1
        out = ROOT / "store" / "summaries" / p["slug"] / f"v{nv}.md"
        if out.exists():
            log.info(f"skip (v{nv} exists): {(p['title'] or '')[:50]}")
            continue
        todo.append({"paperId": p["id"], "title": p["title"], "issues": w["issues"],
                     "currentPath": str(ROOT / cur["path"]), "nextVersion": nv, "outPath": str(out),
                     "text_path": str(ROOT / p["text_path"]) if p["text_path"] else None,
                     "pdf_path": str(ROOT / p["pdf_path"]) if p["pdf_path"] else None})
    conn.close()
    log.info(f"correct_summaries: {len(work)} in worklist, {len(todo)} to do, concurrency={concurrency}")

    def worker(w, _i):
        text = full_text(w)
        if not text:
            raise RuntimeError("no fulltext")
        current_md = Path(w["currentPath"]).read_text(encoding="utf-8", errors="ignore")
        md = run_claude(cprompt(w["title"], current_md, w["issues"], w["nextVersion"],
                                w["paperId"], text[:MAX_CHARS]))
        if not md or len(md) < 200:
            raise RuntimeError(f"bad output ({len(md)} chars)")
        Path(w["outPath"]).parent.mkdir(parents=True, exist_ok=True)
        Path(w["outPath"]).write_text(md, encoding="utf-8")
        log.info(f"  OK v{w['nextVersion']} {(w['title'] or '')[:50]}")
        return w

    res = pool(todo, worker, concurrency)
    done = [r for r in res if isinstance(r, dict) and r.get("outPath") and Path(r["outPath"]).exists()]

    conn = open_db()
    for w in done:
        rel = str(Path(w["outPath"]).relative_to(ROOT))
        conn.execute(
            """INSERT OR IGNORE INTO summary_versions (paper_id,version,path,based_on,note,created_at)
               VALUES (?,?,?,?,?,?)""",
            (w["paperId"], w["nextVersion"], rel, "[]",
             f"事实核查修正(Codex 抽检发现 {len(w['issues'])} 处问题)", now_iso()))
        conn.execute("UPDATE papers SET summarized_at=? WHERE id=?", (now_iso(), w["paperId"]))
    conn.commit()
    conn.close()
    log.info(f"correct_summaries done: {len(done)}/{len(todo)} corrected+registered")
    run_log("-", f"correct_summaries: {len(done)}/{len(todo)} corrected")
    return done


def main():
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    wl = ROOT / "store" / "correction_worklist.json"
    if not wl.exists():
        print("no correction_worklist.json", file=sys.stderr)
        sys.exit(1)
    work = json.loads(wl.read_text(encoding="utf-8"))["work"]
    run_corrections(work, concurrency)


if __name__ == "__main__":
    main()
