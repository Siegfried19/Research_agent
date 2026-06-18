"""After summarization, register v1 summaries and mark papers summarized.
Usage: python3 pipeline/summarize/register_summaries.py <topicId|all>
"""
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT, now_iso
from lib.slug import file_id


def main():
    topic_id = sys.argv[1] if len(sys.argv) > 1 else "all"
    conn = open_db()
    if topic_id == "all":
        rows = conn.execute("SELECT id, slug FROM papers WHERE status='pdf_downloaded'").fetchall()
    else:
        rows = conn.execute(
            """SELECT p.id, p.slug FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                WHERE pt.topic_id=? AND p.status='pdf_downloaded'""", (topic_id,)).fetchall()

    registered, missing = 0, 0
    for r in rows:
        vpath = ROOT / "store" / "summaries" / (r["slug"] or file_id(r["id"])) / "v1.md"
        if not vpath.exists() or vpath.stat().st_size < 100:
            missing += 1
            continue
        rel = str(vpath.relative_to(ROOT))
        conn.execute(
            """INSERT OR IGNORE INTO summary_versions (paper_id,version,path,based_on,note,created_at)
               VALUES (?,?,?,?,?,?)""", (r["id"], 1, rel, "[]", "首次总结", now_iso()))
        conn.execute("UPDATE papers SET status='summarized', summarized_at=? WHERE id=?", (now_iso(), r["id"]))
        registered += 1
    conn.commit()
    conn.close()
    print(f"registered {registered} v1 summaries; {missing} still missing a summary file")


if __name__ == "__main__":
    main()
