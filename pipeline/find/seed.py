"""Seed specific papers into a topic's candidate pool by id — bypass keyword search + prefilter.

A point-name channel for foundational papers the keyword search misses or truncates:
  - topic.json `seed_ids` (user-specified must-haves)
  - `turning_seeds` ids the orchestrator discovers by following citations

Usage:
  python3 pipeline/find/seed.py <topicId> <id> [<id> ...]
  ids: DOI / arxiv id / OpenAlex W-id / PMID / URL (doi.org, arxiv.org, openalex.org)

Prints a JSON summary to stdout (seeded / already / failed) so a caller (orchestrator) can read it.
"""
import json
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT, load_config, now_iso
from lib import sources
from lib import pool as poolmod
from lib import topic as T
from lib.http import sleep
from lib.log import get_logger, run_log

config = load_config()
log = get_logger("seed")


def load_or_init_candidates(topic_id):
    """Reuse an existing pool (seeding after discover), or build a skeleton (seeding first)."""
    data = poolmod.load_candidates(topic_id)
    if data:
        return data
    tj = ROOT / "topics" / topic_id / "topic.json"
    topic = json.loads(tj.read_text(encoding="utf-8")) if tj.exists() else {"id": topic_id}
    return {
        "topic": {"id": topic_id, "title": topic.get("title"), "idea": topic.get("idea"),
                  "queries": topic.get("queries", [])},
        "window": None, "target": topic.get("target"), "generated_at": now_iso(),
        "raw_records": 0, "merged_unique": 0, "pool": 0, "candidates": [],
    }


def main():
    if len(sys.argv) < 3:
        print("usage: seed.py [--facet <key>] <topicId> <id> [<id> ...]", file=sys.stderr)
        sys.exit(1)
    argv = sys.argv[1:]
    facet_override = None
    if "--facet" in argv:
        i = argv.index("--facet")
        facet_override = argv[i + 1]
        del argv[i:i + 2]
    topic_id = argv[0]
    ids = argv[1:]
    edge_thr = config["ranking"]["edge_citation_threshold"]

    # seed_ids live per-facet in topic.json; map each id -> its facet so faceted
    # scoring/commit groups the seed correctly ('_all' would fall through all facets
    # and never get scored). --facet overrides (for turning seeds not in topic.json).
    seed_facet = {}
    tj = ROOT / "topics" / topic_id / "topic.json"
    if tj.exists():
        for fac in T.load_topic(tj)["facets"]:
            for sid in fac["seed_ids"]:
                seed_facet[sid] = fac["key"]

    def facet_for(raw):
        return facet_override or seed_facet.get(raw, "_all")

    data = load_or_init_candidates(topic_id)
    cands = data["candidates"]
    existing = set()
    for c in cands:
        existing |= poolmod.candidate_keys(c)

    seeded, already, failed = [], [], []
    log.info(f"# Seed {topic_id}: {len(ids)} id(s)")
    for raw in ids:
        kind, _ = sources.parse_ident(raw)
        try:
            rec = sources.fetch_by_id(raw)
        except Exception as e:  # noqa: BLE001
            rec = None
            log.info(f"  FETCH-ERR {raw}: {e}")
        if not rec:
            failed.append({"input": raw, "kind": kind})
            log.info(f"  FAIL [{kind}] {raw} -> not found")
            sleep(0.7)
            continue
        fac = facet_for(raw)
        cand = poolmod.record_to_candidate(rec, edge_thr, seeded=True, facet=fac)
        keys = poolmod.candidate_keys(cand)
        if keys & existing:
            for c in cands:  # already present — promote to seeded so truncation/cuts can't drop it
                if poolmod.candidate_keys(c) & keys:
                    c["seeded"] = True
                    if fac != "_all":
                        c["facet"] = fac  # explicit per-facet seed intent wins over discover's keyword-match tag
            already.append({"input": raw, "id": cand["id"], "title": cand["title"]})
            log.info(f"  ALREADY [{kind}] {cand['title'][:70]} (marked seeded)")
        else:
            cands.append(cand)
            existing |= keys
            tier = cand["quality"]["tier"]
            warn = "  ⚠ quality=block(commit 不会入库)" if tier == "block" else ""
            seeded.append({"input": raw, "id": cand["id"], "title": cand["title"],
                           "quality": tier, "has_abstract": bool(cand["abstract"])})
            log.info(f"  SEED [{kind}] {cand['title'][:70]} (q={tier}){warn}")
        sleep(0.7)

    data["pool"] = len(cands)
    poolmod.save_candidates(topic_id, data)
    run_log(topic_id, f"seed: +{len(seeded)} already={len(already)} failed={len(failed)} pool={len(cands)}")
    log.info(f"# Done: seeded {len(seeded)}  already {len(already)}  failed {len(failed)}  pool {len(cands)}")
    print(json.dumps({"seeded": seeded, "already": already, "failed": failed,
                      "pool_size": len(cands)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
