"""Build a summarization worklist for a topic (sources with a PDF, not yet summarized).
Usage: python3 pipeline/summarize/build_worklist.py <topicId>
"""
import json
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT
from lib.slug import file_id
from lib.store import paper_dir


def main():
    if len(sys.argv) < 2:
        print("usage: build_worklist.py <topicId>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    conn = open_db()
    rows = conn.execute(
        """SELECT p.*, pt.relevance, pt.relevance_reason
             FROM sources p JOIN source_topic pt ON pt.paper_id=p.id
            WHERE pt.topic_id=? AND p.status='source_ready'
              AND (p.kind IS NULL OR p.kind!='web')  -- web(blog等)先不总结,只总结论文
            ORDER BY pt.rank""", (topic_id,)).fetchall()
    conn.close()

    work = []
    for r in rows:
        base = r["slug"] or file_id(r["id"])
        sdir = paper_dir(base)
        work.append({
            "id": r["id"], "title": r["title"], "authors": json.loads(r["authors"] or "[]"),
            "year": r["year"], "venue": r["venue"], "citation_count": r["citation_count"],
            "doi": r["doi"], "landing_url": r["landing_url"], "is_edge": bool(r["is_edge"]),
            "relevance": r["relevance"], "relevance_reason": r["relevance_reason"],
            "quality_tier": r["quality_tier"], "quality_signals": r["quality_signals"],
            "source_path": str(ROOT / r["source_path"]) if r["source_path"] else None,
            "summary_dir": str(sdir),
            "summary_path": str(sdir / "v1.md"),
        })

    out = ROOT / "topics" / topic_id / "summarize_worklist.json"
    out.write_text(json.dumps({"topicId": topic_id, "total": len(work), "work": work},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"worklist: {len(work)} sources -> topics/{topic_id}/summarize_worklist.json")
    print(f"  with-pdf: {sum(1 for w in work if w['source_path'])}")


if __name__ == "__main__":
    main()
