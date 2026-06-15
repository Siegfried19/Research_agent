"""Suggest which existing summaries are worth updating because new citation-neighbors
have since been summarized.
Usage: python3 pipeline/tools/suggest_updates.py <topicId|all>
"""
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db


def main():
    topic_id = sys.argv[1] if len(sys.argv) > 1 else "all"
    conn = open_db()
    if topic_id == "all":
        papers = conn.execute("SELECT id, title FROM papers WHERE status='summarized'").fetchall()
    else:
        papers = conn.execute(
            """SELECT p.id, p.title FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                WHERE pt.topic_id=? AND p.status='summarized'""", (topic_id,)).fetchall()

    suggestions = []
    for p in papers:
        v = conn.execute("SELECT MAX(version) v, MAX(created_at) c FROM summary_versions WHERE paper_id=?",
                         (p["id"],)).fetchone()
        since = v["c"] if v else None
        neigh = conn.execute(
            """SELECT DISTINCT q.id, q.title FROM papers q
                WHERE q.status='summarized' AND q.id<>?
                  AND (q.id IN (SELECT dst_paper_id FROM citations WHERE src_paper_id=?)
                    OR q.id IN (SELECT src_paper_id FROM citations WHERE dst_paper_id=?))
                  AND (? IS NULL OR q.summarized_at > ?)""",
            (p["id"], p["id"], p["id"], since, since)).fetchall()
        if neigh:
            suggestions.append({"id": p["id"], "title": p["title"],
                                "current_version": v["v"], "new_related": [dict(n) for n in neigh]})
    conn.close()

    print(f"# Update suggestions ({len(suggestions)})")
    for s in suggestions:
        print(f"  [{len(s['new_related'])} new related] v{s['current_version']} {(s['title'] or '')[:50]}")
    if suggestions:
        print(f"\nTo update, e.g.:  python3 pipeline/tools/prepare_update.py {suggestions[0]['id']}")


if __name__ == "__main__":
    main()
