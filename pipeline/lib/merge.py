"""Dedup + merge normalized records from multiple sources into canonical papers."""
import hashlib
import re
import unicodedata

_NT = re.compile(r"[^a-z0-9぀-ヿ一-鿿]+")


def norm_title(t):
    s = unicodedata.normalize("NFKD", (t or "").lower())
    return _NT.sub(" ", s).strip()


def canonical_id(rec):
    if rec.get("doi"):
        return rec["doi"]
    ext = rec.get("ext_ids") or {}
    if ext.get("arxiv"):
        return "arxiv:" + ext["arxiv"]
    h = hashlib.sha1(norm_title(rec.get("title")).encode("utf-8")).hexdigest()[:16]
    return "title:" + h


def _longer(a, b):
    return b if (b and len(b) > (len(a) if a else 0)) else a


def _merge_into(dst, rec):
    dst["sources"].add(rec["source"])
    rr = rec.get("relRank")
    prev = dst["relRankBySource"].get(rec["source"], float("inf"))
    dst["relRankBySource"][rec["source"]] = min(prev, rr if rr is not None else float("inf"))
    dst["title"] = dst["title"] or rec.get("title")
    dst["doi"] = dst["doi"] or rec.get("doi")
    dst["year"] = dst["year"] or rec.get("year")
    dst["venue"] = dst["venue"] or rec.get("venue")
    dst["abstract"] = _longer(dst["abstract"], rec.get("abstract"))
    dst["language"] = dst["language"] or rec.get("language")
    dst["citation_count"] = max(dst["citation_count"] or 0, rec.get("citation_count") or 0)
    dst["is_oa"] = dst["is_oa"] or rec.get("is_oa")
    dst["oa_url"] = dst["oa_url"] or rec.get("oa_url")
    dst["landing_url"] = dst["landing_url"] or rec.get("landing_url")
    authors = rec.get("authors") or []
    if len(authors) > len(dst["authors"] or []):
        dst["authors"] = authors
    for k, v in (rec.get("ext_ids") or {}).items():
        if v:
            dst["ext_ids"][k] = v
    for r in rec.get("ref_ext_ids") or []:
        dst["refSet"].add(r)
    for q in rec.get("_queries") or []:
        dst["queries"].add(q)


def merge_all(records):
    by_id = {}
    title_index = {}  # norm_title -> canonical id (catch DOI-vs-title dupes)

    for rec in records:
        cid = canonical_id(rec)
        nt = norm_title(rec.get("title"))
        if cid not in by_id and nt and nt in title_index:
            cid = title_index[nt]
        if cid not in by_id:
            by_id[cid] = {
                "id": cid, "title": "", "doi": None, "authors": [], "year": None,
                "venue": None, "abstract": None, "language": None, "citation_count": 0,
                "is_oa": False, "oa_url": None, "landing_url": None,
                "sources": set(), "relRankBySource": {}, "ext_ids": {},
                "refSet": set(), "queries": set(),
            }
        _merge_into(by_id[cid], rec)
        if nt:
            title_index[nt] = cid

    out = []
    for p in by_id.values():
        out.append({
            **p,
            "sources": list(p["sources"]),
            "ref_ext_ids": list(p["refSet"]),
            "queries": list(p["queries"]),
        })
        out[-1].pop("refSet", None)
    return out
