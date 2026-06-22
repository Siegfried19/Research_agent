"""Topic archive layer: intent (topic.json) + state (topic_state.json).

Two files on purpose (see find-facet-rewrite-design.md §1):
  - topic.json       intent — defined in discussion, pipeline rarely rewrites it
  - topic_state.json state  — pipeline/orchestrator writes each run

load_topic() normalizes topic.json into an ALWAYS-FACETED form so downstream code
(score/commit) can iterate facets uniformly. Backward compatible: a topic with no
`facets` degrades to a single implicit facet built from the global idea/queries/anchors
(== current single-ruler behavior; existing gt/dhi topics keep working untouched).
"""
import json
from datetime import datetime
from pathlib import Path

from .db import ROOT

IMPLICIT_FACET_KEY = "_all"


def _topic_path(ref):
    s = str(ref)
    return Path(s) if s.endswith(".json") else ROOT / "topics" / s / "topic.json"


def _norm_facet(f, raw):
    """Normalize one explicit facet; missing hit_criteria falls back to global preferences."""
    return {
        "key": f.get("key") or f.get("title") or "facet",
        "title": f.get("title") or f.get("key") or "",
        "hit_criteria": f.get("hit_criteria") or raw.get("preferences") or "",
        "queries": f.get("queries") or [],
        "anchors": f.get("anchors") or [],
        "seed_ids": f.get("seed_ids") or [],
        "note": f.get("note") or "",
    }


def load_topic(ref):
    """Load topic.json (by id or path) and normalize to always-faceted form.

    Returns: {id, title, idea, window_years, target, preferences, web_sources,
              facets[normalized], _faceted(bool), _raw(original dict)}.
    """
    raw = json.loads(_topic_path(ref).read_text(encoding="utf-8"))
    faceted = bool(raw.get("facets"))
    if faceted:
        facets = [_norm_facet(f, raw) for f in raw["facets"]]
    else:
        facets = [{
            "key": IMPLICIT_FACET_KEY,
            "title": raw.get("title") or raw.get("id"),
            "hit_criteria": raw.get("preferences") or "",
            "queries": raw.get("queries") or [],
            "anchors": raw.get("score_anchors") or [],
            "seed_ids": raw.get("seed_ids") or [],
            "note": "",
        }]
    return {
        "id": raw["id"],
        "title": raw.get("title"),
        "idea": raw.get("idea"),
        "window_years": raw.get("window_years"),
        "target": raw.get("target"),
        "preferences": raw.get("preferences") or "",
        "web_sources": raw.get("web_sources") or [],
        "facets": facets,
        "_faceted": faceted,
        "_raw": raw,
    }


def facet_by_key(topic, key):
    return next((f for f in topic["facets"] if f["key"] == key), None)


def _union(lists):
    seen, out = set(), []
    for item in lists:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def all_queries(topic):
    """Union of every facet's queries (order-preserving, deduped)."""
    return _union(q for f in topic["facets"] for q in f["queries"])


# ---------------- topic_state.json ----------------
def _state_path(topic_id):
    return ROOT / "topics" / topic_id / "topic_state.json"


def load_state(topic_id):
    p = _state_path(topic_id)
    if p.exists():
        st = json.loads(p.read_text(encoding="utf-8"))
        st.setdefault("facets", {})
        st.setdefault("turning_seeds", [])
        return st
    return {"facets": {}, "turning_seeds": []}


def save_state(topic_id, state):
    p = _state_path(topic_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def record_find(topic_id, per_facet_added, topic_total):
    """Code-driven 留痕: called by commit.py right after it writes the DB, so the
    NUMERIC state (in_db_total / last_find / per-facet committed) is always synced
    to the DB and never drifts — even if the find orchestrator forgets to Write it.

    Only touches numbers; the qualitative fields (coverage / note / turning_seeds)
    stay agent-owned and are left untouched. per_facet_added counts THIS round's
    newly-committed papers per facet; commit only adds fresh rows on incremental
    runs, so accumulating is double-count-safe across idempotent re-runs.
    """
    state = load_state(topic_id)
    state["in_db_total"] = topic_total
    state["last_find"] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    facets = state.setdefault("facets", {})
    for fkey, added in per_facet_added.items():
        if not added:
            continue
        f = facets.setdefault(fkey, {})
        f["committed"] = int(f.get("committed", 0)) + int(added)
    save_state(topic_id, state)
