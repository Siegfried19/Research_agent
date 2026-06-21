"""After relevance scoring: merge scores, select, write to DB (additive on incremental).
Usage: python3 pipeline/find/commit.py topics/<slug>
"""
import json
import sys
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, load_config
from lib import store
from lib.log import get_logger, run_log
from lib import quality

config = load_config()
log = get_logger("commit")


def parse_keep(spec):
    """'all' -> keep every eligible; 'f1=10,f2=5,*=8' -> per-facet keep counts (None=all)."""
    if spec.strip() == "all":
        return {"*": None}
    out = {}
    for part in spec.split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k.strip()] = None if v.strip() in ("all", "*") else int(v.strip())
    return out


def _buckets(plist):
    b = {">=80": 0, "60-79": 0, "45-59": 0, "30-44": 0}
    for p in plist:
        r = p["relevance"]
        b[">=80" if r >= 80 else "60-79" if r >= 60 else "45-59" if r >= 45 else "30-44"] += 1
    return b


def emit_plan(by_facet, existing, incremental):
    """Per-facet distribution for the orchestrator to read (no DB write)."""
    plan = {"mode": "incremental" if incremental else "first-run", "facets": []}
    for fkey, plist in by_facet.items():
        plan["facets"].append({
            "facet": fkey,
            "eligible": len(plist),
            "fresh": sum(1 for p in plist if p["id"] not in existing),
            "buckets": _buckets(plist),
            "papers": [{"id": p["id"], "rel": p["relevance"], "q": p["quality"]["tier"],
                        "seeded": p.get("seeded", False), "in_db": p["id"] in existing,
                        "title": (p["title"] or "")[:90]} for p in plist],
        })
    print(json.dumps(plan, ensure_ascii=False, indent=2))


def select_by_keep(by_facet, keep, existing, incremental):
    """Keep top-N eligible per facet (N from `keep`; unlisted facet -> keep all)."""
    selected = []
    for fkey, plist in by_facet.items():
        avail = [p for p in plist if not incremental or p["id"] not in existing]
        n = keep.get(fkey, keep.get("*"))
        selected.extend(avail if n is None else avail[:n])
    return selected


def main():
    args = sys.argv[1:]
    plan_mode = "--plan" in args
    if plan_mode:
        args.remove("--plan")
    keep_spec = None
    if "--keep" in args:
        i = args.index("--keep")
        keep_spec = parse_keep(args[i + 1])
        del args[i:i + 2]
    if not args:
        print("usage: commit.py topics/<slug> [--plan] [--keep all|f1=N,f2=M]", file=sys.stderr)
        sys.exit(1)
    topic_dir = Path(args[0]).resolve()
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
        if p.get("seeded"):  # 用户点名的必进奠基作:绕过相关性/flag/panel 闸(block 已挡在前)
            log.info(f"  SEED-FORCE-IN [rel={p['relevance']}] {p['title'][:70]}")
            eligible.append(p)
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

    # facet grouping: every candidate carries a 'facet' tag ('_all' for non-faceted topics)
    from collections import OrderedDict
    by_facet = OrderedDict()
    for p in eligible:  # eligible already sorted by relevance desc
        by_facet.setdefault(p.get("facet") or "_all", []).append(p)

    if plan_mode:  # orchestrator reads the per-facet distribution, then decides --keep
        conn.close()
        emit_plan(by_facet, existing, incremental)
        return

    if keep_spec is not None:  # orchestrator-driven per-facet selection
        selected = select_by_keep(by_facet, keep_spec, existing, incremental)
    elif not incremental:
        selected = eligible[:target]
    else:
        fresh = [p for p in eligible if p["id"] not in existing]
        cap = target * 3
        selected = fresh[:cap]
        if len(fresh) > cap:
            log.info(f"  note: {len(fresh)} new eligible, capped to {cap}")

    # seed 必进:所有 seeded 篇(非 block、不在已库、未被选中)强制带上,不受 keep/top-N 截断
    sel_ids = {p["id"] for p in selected}
    forced = [p for p in eligible if p.get("seeded") and p["id"] not in sel_ids and p["id"] not in existing]
    if forced:
        selected = selected + forced
        log.info(f"  seed force-include: +{len(forced)} 篇必进(绕过 keep/top-N 截断)")

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
          "edge": p["edge_insight"], "is_oa": p["is_oa"], "facet": p.get("facet", "_all")} for p in selected],
        ensure_ascii=False, indent=2), encoding="utf-8")

    mode = "INCREMENTAL" if incremental else "FIRST RUN"
    sel_method = f"keep={keep_spec}" if keep_spec is not None else "auto"
    log.info(f"# Commit: {topic['id']}  [{mode}]  ({sel_method})")
    log.info(f"  scored {len(score_by_id)}/{len(cand['candidates'])}  eligible {len(eligible)}  added {len(selected)}")
    if len(by_facet) > 1:
        from collections import Counter
        per = Counter(p.get("facet", "_all") for p in selected)
        log.info(f"  per-facet added: {dict(per)}")
    log.info(f"  quality gate: blocked {n_qblock}, flagged-out {n_qflag_out}, suspect-in {n_qsuspect}, "
             f"panel-out {n_panel_out} (flag/suspect 需 relevance>={flag_min})")
    log.info(f"  topic now has {topic_total} papers  (new-to-db {n_new}, reused {n_existing}, OA {n_oa}, edge {n_edge})")
    log.info(f"  citation edges (topic): {edges}")
    run_log(topic["id"], f"commit[{mode}]: added={len(selected)} total={topic_total} edges={edges} qblock={n_qblock} qflagout={n_qflag_out} qsuspect={n_qsuspect}")


if __name__ == "__main__":
    main()
