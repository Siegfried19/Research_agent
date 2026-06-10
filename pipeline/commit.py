"""After relevance scoring: merge scores, select, write to DB (additive on incremental).
Usage: python3 pipeline/commit.py topics/<slug>
"""
import json
import sys
from pathlib import Path

from lib.db import open_db, ROOT, load_config
from lib import store
from lib.log import get_logger, run_log
from lib import quality

config = load_config()
log = get_logger("commit")


def main():
    if len(sys.argv) < 2:
        print("usage: commit.py topics/<slug>", file=sys.stderr)
        sys.exit(1)
    topic_dir = Path(sys.argv[1]).resolve()
    cand = json.loads((topic_dir / "candidates.json").read_text(encoding="utf-8"))
    score_dir = topic_dir / "scores"
    topic = cand["topic"]
    target = cand.get("target") or config["first_run_target"]

    score_by_id = {}
    if score_dir.exists():
        for f in sorted(score_dir.glob("*.json")):
            for s in json.loads(f.read_text(encoding="utf-8")):
                score_by_id[s["id"]] = s

    qcfg = config.get("quality") or {}
    flag_min = qcfg.get("flag_min_relevance", 45)

    scored = []
    n_qblock = n_qflag_out = n_panel_out = 0
    for p in cand["candidates"]:
        s = score_by_id.get(p["id"], {})
        q = p.get("quality") or quality.assess(p)  # 老 candidates.json 没有 quality 字段,现算
        scored.append({**p, "quality": q, "relevance": s.get("relevance", 0),
                       "relevance_reason": s.get("reason") or "(未打分)",
                       "edge_insight": bool(s.get("edge_insight")),
                       "panel_objection": s.get("panel_objection")})

    n_qsuspect = 0
    eligible = []
    for p in sorted(scored, key=lambda p: (p["relevance"], p.get("citation_count") or 0), reverse=True):
        tier = p["quality"]["tier"]
        if tier == "block":
            n_qblock += 1
            log.info(f"  QUALITY-BLOCK [{','.join(p['quality']['signals'])}] {p['title'][:70]}")
            continue
        if not (p["relevance"] >= 30 or p["edge_insight"]):
            continue
        # flag(预印本/无venue)和 suspect(掠夺名单命中)都要更高的相关性才入选
        if tier in ("flag", "suspect") and p["relevance"] < flag_min and not p["edge_insight"]:
            n_qflag_out += 1
            log.info(f"  QUALITY-{tier.upper()}-OUT [{','.join(p['quality']['signals'])} rel={p['relevance']}<{flag_min}] {p['title'][:70]}")
            continue
        if tier == "suspect":
            n_qsuspect += 1
            log.info(f"  QUALITY-SUSPECT-IN(带标记入库,总结走质疑模式) [{','.join(p['quality']['signals'])}] {p['title'][:70]}")
        # 评审团合议:Codex 无否决权——边界分(<60)+异议=挡下;高分+异议=入库但把异议记进理由
        if p.get("panel_objection"):
            if p["relevance"] < 60 and not p["edge_insight"]:
                n_panel_out += 1
                log.info(f"  PANEL-OUT [rel={p['relevance']} Codex异议] {p['title'][:60]} — {p['panel_objection']}")
                continue
            p["relevance_reason"] = f"{p['relevance_reason']}；[Codex异议]{p['panel_objection']}"
            log.info(f"  PANEL-NOTE(入库带异议) [rel={p['relevance']}] {p['title'][:60]}")
        eligible.append(p)

    conn = open_db()
    store.upsert_topic(conn, topic, target)
    existing = {r["paper_id"] for r in
                conn.execute("SELECT paper_id FROM paper_topic WHERE topic_id=?", (topic["id"],)).fetchall()}
    incremental = len(existing) > 0

    if not incremental:
        selected = eligible[:target]
    else:
        fresh = [p for p in eligible if p["id"] not in existing]
        cap = target * 3
        selected = fresh[:cap]
        if len(fresh) > cap:
            log.info(f"  note: {len(fresh)} new eligible, capped to {cap}")

    n_new = n_existing = n_oa = n_edge = 0
    for p in selected:
        if store.upsert_paper(conn, p) == "new":
            n_new += 1
        else:
            n_existing += 1
        if p["is_oa"]:
            n_oa += 1
        if p["edge_insight"]:
            n_edge += 1
        store.set_paper_topic(conn, topic["id"], p, 0)  # rank recomputed below

    all_pt = conn.execute(
        """SELECT pt.paper_id, pt.relevance, p.citation_count
             FROM paper_topic pt JOIN papers p ON p.id=pt.paper_id
            WHERE pt.topic_id=? ORDER BY pt.relevance DESC, p.citation_count DESC""", (topic["id"],)).fetchall()
    for i, row in enumerate(all_pt):
        conn.execute("UPDATE paper_topic SET rank=? WHERE topic_id=? AND paper_id=?",
                     (i + 1, topic["id"], row["paper_id"]))

    full_set = [{"id": r["id"], "ext_ids": json.loads(r["ext_ids"] or "{}"),
                 "ref_ext_ids": json.loads(r["ref_ext_ids"] or "[]")}
                for r in conn.execute(
                    """SELECT p.id, p.ext_ids, p.ref_ext_ids FROM papers p
                        JOIN paper_topic pt ON pt.paper_id=p.id WHERE pt.topic_id=?""", (topic["id"],)).fetchall()]
    edges = store.build_citations(conn, full_set)
    topic_total = len(all_pt)
    conn.commit()
    conn.close()

    (topic_dir / "selected.json").write_text(json.dumps(
        [{"id": p["id"], "title": p["title"], "relevance": p["relevance"], "reason": p["relevance_reason"],
          "edge": p["edge_insight"], "is_oa": p["is_oa"]} for p in selected],
        ensure_ascii=False, indent=2), encoding="utf-8")

    mode = "INCREMENTAL" if incremental else "FIRST RUN"
    log.info(f"# Commit: {topic['id']}  [{mode}]")
    log.info(f"  scored {len(score_by_id)}/{len(cand['candidates'])}  eligible {len(eligible)}  added {len(selected)}")
    log.info(f"  quality gate: blocked {n_qblock}, flagged-out {n_qflag_out}, suspect-in {n_qsuspect}, "
             f"panel-out {n_panel_out} (flag/suspect 需 relevance>={flag_min})")
    log.info(f"  topic now has {topic_total} papers  (new-to-db {n_new}, reused {n_existing}, OA {n_oa}, edge {n_edge})")
    log.info(f"  citation edges (topic): {edges}")
    run_log(topic["id"], f"commit[{mode}]: added={len(selected)} total={topic_total} edges={edges} qblock={n_qblock} qflagout={n_qflag_out} qsuspect={n_qsuspect}")


if __name__ == "__main__":
    main()
