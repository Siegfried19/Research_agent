"""Candidate-pool helpers shared by discover (keyword search) and seed (by-id).

A "candidate entry" is the per-paper dict stored in topics/<id>/candidates.json,
consumed downstream by score_auto / commit. Both discovery and seeding funnel
through candidate_entry() so the on-disk shape stays identical.
"""
import json

from .db import ROOT
from .merge import merge_all
from . import quality


def candidate_entry(p, edge_thr, seeded=False, facet="_all"):
    """Build one candidates.json entry from a merged paper `p` (output of merge_all,
    with `quality` assessed and an optional `_pre` prefilter score).
    `facet` = which subtopic found this paper ('_all' for non-faceted topics)."""
    return {
        "id": p["id"], "doi": p["doi"], "title": p["title"], "authors": p["authors"], "year": p["year"],
        "venue": p["venue"], "publisher": p.get("publisher"), "is_in_doaj": bool(p.get("is_in_doaj")),
        "is_retracted": bool(p.get("is_retracted")), "abstract": p["abstract"], "language": p["language"],
        "citation_count": p["citation_count"], "is_oa": p["is_oa"], "oa_url": p["oa_url"],
        "landing_url": p["landing_url"], "sources": p["sources"], "ext_ids": p["ext_ids"],
        "ref_ext_ids": p.get("ref_ext_ids", []), "matched_queries": p.get("queries", []),
        "is_edge": (p["citation_count"] or 0) < edge_thr,
        "prefilter": round(p.get("_pre", 0.0), 3),
        "quality": p["quality"],
        "seeded": seeded,
        "facet": facet,
    }


def record_to_candidate(rec, edge_thr, seeded=True, facet="_all"):
    """Single normalized source record -> merged paper -> quality -> candidate entry."""
    merged = merge_all([rec])[0]
    merged["quality"] = quality.assess(merged)
    return candidate_entry(merged, edge_thr, seeded=seeded, facet=facet)


def candidate_keys(c):
    """Dedup keys for a candidate entry: canonical id + doi + arxiv ext id."""
    keys = set()
    if c.get("id"):
        keys.add(c["id"])
    if c.get("doi"):
        keys.add("doi:" + c["doi"])
    ext = c.get("ext_ids") or {}
    if ext.get("arxiv"):
        keys.add("arxiv:" + ext["arxiv"])
    return keys


def candidates_path(topic_id):
    return ROOT / "topics" / topic_id / "candidates.json"


def load_candidates(topic_id):
    p = candidates_path(topic_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_candidates(topic_id, data):
    p = candidates_path(topic_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
