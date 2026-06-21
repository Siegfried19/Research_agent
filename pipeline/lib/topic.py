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
from pathlib import Path

from .db import ROOT, now_iso

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


def is_faceted(topic):
    return topic["_faceted"]


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


def all_seed_ids(topic):
    """Union of every facet's seed_ids (order-preserving, deduped)."""
    return _union(s for f in topic["facets"] for s in f["seed_ids"])


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


def update_facet_state(topic_id, facet_key, *, in_db=None, coverage=None, last_run=None):
    """Merge per-facet coverage/in_db/last_run into topic_state.json (additive)."""
    state = load_state(topic_id)
    fs = state["facets"].setdefault(facet_key, {})
    if in_db is not None:
        fs["in_db"] = in_db
    if coverage is not None:
        fs["coverage"] = coverage
    fs["last_run"] = last_run or now_iso()[:10]
    save_state(topic_id, state)
    return state


def add_turning_seed(topic_id, seed):
    """Append a turning seed: {hint|id, from, kind: 'query'|'id'}."""
    state = load_state(topic_id)
    state["turning_seeds"].append(seed)
    save_state(topic_id, state)
    return state
