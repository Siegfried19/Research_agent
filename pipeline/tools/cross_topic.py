"""Find papers shared across topics + citation bridges between topics.
Writes store/cross_topic.json. Usage: python3 pipeline/tools/cross_topic.py
"""
import json

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT
from lib.store import build_citations


def main():
    conn = open_db()
    topics = conn.execute("SELECT id, title FROM topics").fetchall()

    # commit.py only builds citation edges within each topic's own paper set,
    # so cross-topic edges are missing until we rebuild over the whole library.
    all_papers = [{"id": r["id"], "ext_ids": json.loads(r["ext_ids"] or "{}"),
                   "ref_ext_ids": json.loads(r["ref_ext_ids"] or "[]")}
                  for r in conn.execute("SELECT id, ext_ids, ref_ext_ids FROM papers").fetchall()]
    build_citations(conn, all_papers)  # 副作用:重建全库引用边并落库
    conn.commit()

    topics_by_paper = {}
    for r in conn.execute("SELECT paper_id, topic_id, relevance FROM paper_topic").fetchall():
        topics_by_paper.setdefault(r["paper_id"], []).append({"topic": r["topic_id"], "relevance": r["relevance"]})
    paper_meta = {p["id"]: dict(p) for p in conn.execute("SELECT id, title, year FROM papers").fetchall()}

    shared = []
    for pid, tps in topics_by_paper.items():
        if len(tps) >= 2:
            m = paper_meta.get(pid)
            shared.append({"id": pid, "title": m["title"] if m else None,
                           "year": m["year"] if m else None, "topics": tps})

    def topics_of(pid):
        return [x["topic"] for x in topics_by_paper.get(pid, [])]

    bridges = []
    for e in conn.execute("SELECT src_paper_id s, dst_paper_id d FROM citations").fetchall():
        st, dt = set(topics_of(e["s"])), set(topics_of(e["d"]))
        if st and dt and (st != dt):
            bridges.append({"src": e["s"], "dst": e["d"],
                            "src_title": (paper_meta.get(e["s"]) or {}).get("title") if paper_meta.get(e["s"]) else None,
                            "dst_title": (paper_meta.get(e["d"]) or {}).get("title") if paper_meta.get(e["d"]) else None,
                            "src_topics": list(st), "dst_topics": list(dt)})
    conn.close()

    out = {"generated_topics": len(topics), "shared_papers": shared, "citation_bridges": bridges}
    (ROOT / "storage").mkdir(parents=True, exist_ok=True)
    (ROOT / "storage" / "cross_topic.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"# Cross-topic analysis ({len(topics)} topics)")
    print(f"  shared papers (in >=2 topics): {len(shared)}")
    print(f"  cross-topic citation bridges: {len(bridges)}")
    if len(topics) < 2:
        print("  (need >=2 topics for meaningful cross-topic comparison)")
    print("  -> store/cross_topic.json")


if __name__ == "__main__":
    main()
