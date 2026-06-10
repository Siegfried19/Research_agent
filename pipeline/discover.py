"""Phase 1: multi-source discovery + dedup -> candidate pool (NO db write).
Selection of the final top-N happens after relevance scoring (see score/commit).
Usage: python3 pipeline/discover.py topics/<slug>/topic.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from lib.db import ROOT, load_config, now_iso
from lib import sources
from lib.merge import merge_all
from lib.http import sleep
from lib.log import get_logger, run_log
from lib import quality

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


def prefilter_rank(papers):
    """Recall-oriented prefilter: best position across sources + multi-source agreement.
    Citations are NOT used to select (they over-promote famous-but-off-topic papers)."""
    max_rank = {}
    for p in papers:
        for s, r in p["relRankBySource"].items():
            max_rank[s] = max(max_rank.get(s, 0), r)
    for p in papers:
        best = 0.0
        for s, r in p["relRankBySource"].items():
            denom = max_rank.get(s, 0) + 1
            best = max(best, 1 - r / denom)
        multi = min(0.2, (len(p["sources"]) - 1) * 0.1)
        p["_pre"] = min(1.0, best + multi)
    papers.sort(key=lambda p: p["_pre"], reverse=True)
    return papers


def main():
    if len(sys.argv) < 2:
        print("usage: discover.py topics/<slug>/topic.json", file=sys.stderr)
        sys.exit(1)
    topic = json.loads(Path(sys.argv[1]).resolve().read_text(encoding="utf-8"))
    today = datetime.now()
    from_year = today.year - (topic.get("window_years") or config["window_years"])
    win = {"fromYear": from_year, "toYear": today.year, "fromDate": f"{from_year}-01-01"}
    target = topic.get("target") or config["first_run_target"]
    pool_size = min(500, max(target * 2, 60))

    log.info(f"# Discovery: {topic['title']} ({topic['id']})")
    log.info(f"  window {win['fromDate']}..{win['toYear']}  target {target}  pool {pool_size}  queries {len(topic['queries'])}")
    run_log(topic["id"], f"discover: start target={target} pool={pool_size} queries={len(topic['queries'])}")

    all_recs, lines = gather(topic["queries"], win)
    log.info("\n".join(lines))

    papers = [p for p in merge_all(all_recs) if language_ok(p)]

    # 硬信号挡板:掠夺刊/撤稿在进池前就丢弃(不浪费打分 token)
    kept, blocked = [], []
    for p in papers:
        p["quality"] = quality.assess(p)
        (blocked if p["quality"]["tier"] == "block" else kept).append(p)
    if blocked:
        log.info(f"\n# Quality gate: blocked {len(blocked)}")
        for p in blocked:
            log.info(f"  BLOCK [{','.join(p['quality']['signals'])}] {p['title'][:70]}  ({p.get('venue') or '-'})")
    for p in kept:
        if p["quality"]["tier"] == "suspect":
            log.info(f"  SUSPECT(入池带标记) [{','.join(p['quality']['signals'])}] {p['title'][:70]}  ({p.get('venue') or '-'})")
    papers = prefilter_rank(kept)

    edge_thr = config["ranking"]["edge_citation_threshold"]
    pool = [{
        "id": p["id"], "doi": p["doi"], "title": p["title"], "authors": p["authors"], "year": p["year"],
        "venue": p["venue"], "publisher": p.get("publisher"), "is_in_doaj": bool(p.get("is_in_doaj")),
        "is_retracted": bool(p.get("is_retracted")), "abstract": p["abstract"], "language": p["language"],
        "citation_count": p["citation_count"], "is_oa": p["is_oa"], "oa_url": p["oa_url"],
        "landing_url": p["landing_url"], "sources": p["sources"], "ext_ids": p["ext_ids"],
        "ref_ext_ids": p["ref_ext_ids"], "matched_queries": p["queries"],
        "is_edge": (p["citation_count"] or 0) < edge_thr,
        "prefilter": round(p["_pre"], 3),
        "quality": p["quality"],
    } for p in papers[:pool_size]]

    d = ROOT / "topics" / topic["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "candidates.json").write_text(json.dumps({
        "topic": {"id": topic["id"], "title": topic["title"], "idea": topic["idea"], "queries": topic["queries"]},
        "window": win, "target": target, "generated_at": now_iso(),
        "raw_records": len(all_recs), "merged_unique": len(papers), "pool": len(pool),
        "candidates": pool,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    with_abs = sum(1 for p in pool if p["abstract"])
    oa = sum(1 for p in pool if p["is_oa"])
    log.info(f"\n# Result\n  raw {len(all_recs)}  merged-unique {len(papers)}  pool {len(pool)}")
    log.info(f"  pool has-abstract {with_abs}  OA-downloadable {oa}")
    log.info(f"  -> topics/{topic['id']}/candidates.json  (next: relevance scoring)")
    run_log(topic["id"], f"discover: raw={len(all_recs)} merged={len(papers)} pool={len(pool)} oa={oa} quality_blocked={len(blocked)}")


if __name__ == "__main__":
    main()
