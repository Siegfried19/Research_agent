"""Phase 1: multi-source discovery + dedup -> candidate pool (NO db write).
Selection of the final top-N happens after relevance scoring (see score/commit).
Usage: python3 pipeline/find/discover.py topics/<slug>/topic.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT, load_config, now_iso
from lib import sources
from lib.merge import merge_all
from lib.http import sleep
from lib.log import get_logger, run_log
from lib import quality
from lib import pool as poolmod
from lib import topic as T

config = load_config()
log = get_logger("discover")


def gather(queries, win):
    all_recs, lines = [], []
    fns = {
        "openalex": lambda q: sources.openalex(q, win["fromDate"]),
        "semantic_scholar": lambda q: sources.semantic_scholar(q, win["fromYear"]),
        "arxiv": lambda q: sources.arxiv(q, win["fromYear"]),
        "pubmed": lambda q: sources.pubmed(q, win["fromYear"], win["toYear"]),
    }
    for q in queries:
        for name, fn in fns.items():
            if not config["sources"].get(name):
                continue
            try:
                recs = fn(q)
                for r in recs:
                    r["_queries"] = [q]
                all_recs.extend(recs)
                lines.append(f"  [{name}] \"{q[:48]}\" -> {len(recs)}")
            except Exception as e:  # noqa: BLE001
                lines.append(f"  [{name}] \"{q[:48]}\" -> ERROR {e}")
            sleep(0.7)
    return all_recs, lines


def language_ok(p):
    if config.get("language_strict"):
        return p.get("language") in config["languages"]
    return (not p.get("language")) or (p["language"] in config["languages"])


def prefilter_rank(sources):
    """Recall-oriented prefilter: best position across sources + multi-source agreement.
    Citations are NOT used to select (they over-promote famous-but-off-topic sources)."""
    max_rank = {}
    for p in sources:
        for s, r in p["relRankBySource"].items():
            max_rank[s] = max(max_rank.get(s, 0), r)
    for p in sources:
        best = 0.0
        for s, r in p["relRankBySource"].items():
            denom = max_rank.get(s, 0) + 1
            best = max(best, 1 - r / denom)
        multi = min(0.2, (len(p["sources"]) - 1) * 0.1)
        p["_pre"] = min(1.0, best + multi)
    sources.sort(key=lambda p: p["_pre"], reverse=True)
    return sources


def main():
    args = sys.argv[1:]
    only_facet = None
    if "--facet" in args:
        i = args.index("--facet")
        only_facet = args[i + 1]
        del args[i:i + 2]
    if not args:
        print("usage: discover.py topics/<slug>/topic.json [--facet <key>]", file=sys.stderr)
        sys.exit(1)
    topic = T.load_topic(args[0])

    # query -> facet map + per-candidate tagging (non-faceted topics map everything to '_all')
    qmap, facet_order = {}, [f["key"] for f in topic["facets"]]
    for f in topic["facets"]:
        for q in f["queries"]:
            qmap.setdefault(q, f["key"])

    if only_facet:
        fac = T.facet_by_key(topic, only_facet)
        if not fac:
            print(f"unknown facet '{only_facet}' (have: {facet_order})", file=sys.stderr)
            sys.exit(1)
        queries = fac["queries"]
    else:
        queries = T.all_queries(topic)

    today = datetime.now()
    from_year = today.year - (topic.get("window_years") or config["window_years"])
    win = {"fromYear": from_year, "toYear": today.year, "fromDate": f"{from_year}-01-01"}
    target = topic.get("target") or config["first_run_target"]
    pool_size = min(500, max(target * 2, 60))
    pool_cap = target * 4  # 全局硬顶:不管 agent 怎么 facet 重搜/翻引用合并,candidates.json 非种子候选最多 4×target(防"无限联想"把打分量撑爆+撞超时)

    facet_note = f" facet={only_facet}" if only_facet else (f" faceted={len(facet_order)}" if topic["_faceted"] else "")
    log.info(f"# Discovery: {topic['title']} ({topic['id']}){facet_note}")
    log.info(f"  window {win['fromDate']}..{win['toYear']}  target {target}  pool {pool_size}  queries {len(queries)}")
    run_log(topic["id"], f"discover: start target={target} pool={pool_size} queries={len(queries)}{facet_note}")

    all_recs, lines = gather(queries, win)
    log.info("\n".join(lines))

    sources = [p for p in merge_all(all_recs) if language_ok(p)]

    # 硬信号挡板:掠夺刊/撤稿在进池前就丢弃(不浪费打分 token)
    kept, blocked = [], []
    for p in sources:
        p["quality"] = quality.assess(p)
        (blocked if p["quality"]["tier"] == "block" else kept).append(p)
    if blocked:
        log.info(f"\n# Quality gate: blocked {len(blocked)}")
        for p in blocked:
            log.info(f"  BLOCK [{','.join(p['quality']['signals'])}] {p['title'][:70]}  ({p.get('venue') or '-'})")
    for p in kept:
        if p["quality"]["tier"] == "suspect":
            log.info(f"  SUSPECT(入池带标记) [{','.join(p['quality']['signals'])}] {p['title'][:70]}  ({p.get('venue') or '-'})")
    sources = prefilter_rank(kept)

    edge_thr = config["ranking"]["edge_citation_threshold"]

    def facet_for(p):  # tag by the first facet whose query matched this paper
        for q in (p.get("queries") or []):
            if q in qmap:
                return qmap[q]
        return only_facet or (facet_order[0] if facet_order else "_all")

    new_cands = [poolmod.candidate_entry(p, edge_thr, facet=facet_for(p)) for p in sources[:pool_size]]

    d = ROOT / "topics" / topic["id"]
    d.mkdir(parents=True, exist_ok=True)
    cpath = d / "candidates.json"
    merge_note = ""
    if only_facet and cpath.exists():
        # targeted facet re-search: merge into the existing pool (keep other facets + seeds)
        prev = json.loads(cpath.read_text(encoding="utf-8"))
        cands = prev.get("candidates", [])
        seen = set()
        for c in cands:
            seen |= poolmod.candidate_keys(c)
        added = 0
        for c in new_cands:
            if poolmod.candidate_keys(c) & seen:
                continue
            cands.append(c)
            seen |= poolmod.candidate_keys(c)
            added += 1
        merge_note = f"  (facet merge: +{added} new)"
        # 全局硬顶:种子永留,非种子超出 4×target 的尾部砍掉(防无限联想撑爆打分);砍了就 log,不静默
        if len(cands) > pool_cap:
            seeded = [c for c in cands if c.get("seeded")]
            rest = [c for c in cands if not c.get("seeded")]
            room = max(pool_cap - len(seeded), 0)
            dropped = len(rest) - room
            if dropped > 0:
                cands = seeded + rest[:room]
                merge_note += f"  [pool cap {pool_cap}: 砍尾 {dropped} 非种子]"
                log.info(f"  POOL-CAP: 池超 {pool_cap}(4×target),砍掉 {dropped} 个非种子尾部候选")
    else:
        cands = new_cands

    cpath.write_text(json.dumps({
        "topic": {"id": topic["id"], "title": topic["title"], "idea": topic["idea"], "queries": T.all_queries(topic)},
        "window": win, "target": target, "generated_at": now_iso(),
        "raw_records": len(all_recs), "merged_unique": len(sources), "pool": len(cands),
        "candidates": cands,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    with_abs = sum(1 for p in cands if p["abstract"])
    oa = sum(1 for p in cands if p["is_oa"])
    log.info(f"\n# Result\n  raw {len(all_recs)}  merged-unique {len(sources)}  pool {len(cands)}{merge_note}")
    log.info(f"  pool has-abstract {with_abs}  OA-downloadable {oa}")
    log.info(f"  -> topics/{topic['id']}/candidates.json  (next: relevance scoring)")
    run_log(topic["id"], f"discover: raw={len(all_recs)} merged={len(sources)} pool={len(cands)} oa={oa} quality_blocked={len(blocked)}")


if __name__ == "__main__":
    main()
