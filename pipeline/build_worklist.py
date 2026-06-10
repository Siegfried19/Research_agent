"""Build a summarization worklist for a topic (papers with a PDF, not yet summarized).
Usage: python3 pipeline/build_worklist.py <topicId>
"""
import json
import re
import sys

from lib.db import open_db, ROOT


def file_id(pid):
    return re.sub(r"[^a-z0-9._-]", "_", pid, flags=re.I)[:180]


def main():
    if len(sys.argv) < 2:
        print("usage: build_worklist.py <topicId>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    conn = open_db()
    rows = conn.execute(
        """SELECT p.*, pt.relevance, pt.relevance_reason
             FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
            WHERE pt.topic_id=? AND p.status='pdf_downloaded'
            ORDER BY pt.rank""", (topic_id,)).fetchall()
    conn.close()

    work = []
    for r in rows:
        base = r["slug"] or file_id(r["id"])
        sdir = ROOT / "store" / "summaries" / base
        work.append({
            "id": r["id"], "title": r["title"], "authors": json.loads(r["authors"] or "[]"),
            "year": r["year"], "venue": r["venue"], "citation_count": r["citation_count"],
            "doi": r["doi"], "landing_url": r["landing_url"], "is_edge": bool(r["is_edge"]),
            "relevance": r["relevance"], "relevance_reason": r["relevance_reason"],
            "quality_tier": r["quality_tier"], "quality_signals": r["quality_signals"],
            "text_path": str(ROOT / r["text_path"]) if r["text_path"] else None,
            "pdf_path": str(ROOT / r["pdf_path"]) if r["pdf_path"] else None,
            "summary_dir": str(sdir),
            "summary_path": str(sdir / "v1.md"),
        })

    out = ROOT / "topics" / topic_id / "summarize_worklist.json"
    out.write_text(json.dumps({"topicId": topic_id, "total": len(work), "work": work},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    with_text = sum(1 for w in work if w["text_path"])
    print(f"worklist: {len(work)} papers -> topics/{topic_id}/summarize_worklist.json")
    print(f"  with-text: {with_text}  pdf-only: {sum(1 for w in work if not w['text_path'] and w['pdf_path'])}")


if __name__ == "__main__":
    main()
