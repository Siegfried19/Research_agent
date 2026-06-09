"""Source clients: OpenAlex, Semantic Scholar, arXiv, PubMed.

Each returns a list of normalized record dicts with shape:
  {source, doi, title, authors[], year, venue, abstract, language,
   citation_count, is_oa, oa_url, landing_url, ext_ids{}, ref_ext_ids[], relRank}
"""
import re
from urllib.parse import quote

from .http import get_json, get_text, sleep, HttpError

MAILTO = "a0904251001@gmail.com"


def norm_doi(d):
    if not d:
        return None
    s = re.sub(r"^doi:", "", re.sub(r"^https?://(dx\.)?doi\.org/", "", str(d).lower())).strip()
    return s or None


def abstract_from_inverted(inv):
    if not inv:
        return None
    words = {}
    for w, positions in inv.items():
        for p in positions:
            words[p] = w
    if not words:
        return None
    s = " ".join(words[i] for i in sorted(words)).strip()
    return s or None


# ---------- OpenAlex ----------
def openalex(query, from_date, per_page=120):
    url = (f"https://api.openalex.org/works?search={quote(query)}"
           f"&filter=from_publication_date:{from_date}"
           f"&per-page={per_page}&sort=relevance_score:desc&mailto={MAILTO}")
    data = get_json(url, timeout=45)
    out = []
    for i, w in enumerate(data.get("results") or []):
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        oa = w.get("open_access") or {}
        best = w.get("best_oa_location") or {}
        ids = w.get("ids") or {}
        pmid = ids.get("pmid", "").replace("https://pubmed.ncbi.nlm.nih.gov/", "") if ids.get("pmid") else None
        out.append({
            "source": "openalex",
            "doi": norm_doi(w.get("doi")),
            "title": w.get("display_name") or w.get("title") or "",
            "authors": [a.get("author", {}).get("display_name") for a in (w.get("authorships") or [])
                        if a.get("author", {}).get("display_name")],
            "year": w.get("publication_year"),
            "venue": src.get("display_name"),
            "abstract": abstract_from_inverted(w.get("abstract_inverted_index")),
            "language": w.get("language"),
            "citation_count": w.get("cited_by_count") or 0,
            "is_oa": bool(oa.get("is_oa")),
            "oa_url": oa.get("oa_url") or best.get("pdf_url"),
            "landing_url": w.get("doi") or loc.get("landing_page_url"),
            "ext_ids": {
                "openalex": w["id"].replace("https://openalex.org/", "") if w.get("id") else None,
                "doi": norm_doi(w.get("doi")),
                "pmid": pmid,
            },
            "ref_ext_ids": [r.replace("https://openalex.org/", "") for r in (w.get("referenced_works") or [])],
            "relRank": i,
        })
    return out


# ---------- Semantic Scholar ----------
def semantic_scholar(query, from_year, limit=100):
    fields = "title,abstract,year,authors,venue,externalIds,citationCount,openAccessPdf,publicationTypes"
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}"
           f"&year={from_year}-&fields={fields}&limit={limit}")
    try:
        data = get_json(url, timeout=45, retries=3, retry_delay=3)
    except HttpError as e:
        if e.status == 429:
            return []  # rate-limited without a key; skip gracefully
        raise
    out = []
    for i, p in enumerate(data.get("data") or []):
        ext = p.get("externalIds") or {}
        oapdf = p.get("openAccessPdf") or {}
        out.append({
            "source": "semantic_scholar",
            "doi": norm_doi(ext.get("DOI")),
            "title": p.get("title") or "",
            "authors": [a.get("name") for a in (p.get("authors") or []) if a.get("name")],
            "year": p.get("year"),
            "venue": p.get("venue"),
            "abstract": p.get("abstract"),
            "language": None,
            "citation_count": p.get("citationCount") or 0,
            "is_oa": bool(oapdf.get("url")),
            "oa_url": oapdf.get("url"),
            "landing_url": f"https://doi.org/{ext['DOI']}" if ext.get("DOI") else None,
            "ext_ids": {
                "s2": p.get("paperId"),
                "doi": norm_doi(ext.get("DOI")),
                "arxiv": ext.get("ArXiv"),
                "pmid": ext.get("PubMed"),
            },
            "ref_ext_ids": [],
            "relRank": i,
        })
    return out


# ---------- arXiv (Atom XML, parsed with regex) ----------
def _pick(block, tag):
    m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", block, re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def arxiv(query, from_year, limit=80):
    url = (f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}"
           f"&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending")
    xml = get_text(url, timeout=45)
    blocks = ["<entry>" + part.split("</entry>")[0] for part in xml.split("<entry>")[1:]]
    out = []
    for i, block in enumerate(blocks):
        id_url = _pick(block, "id")
        arxiv_id = re.sub(r"v\d+$", "", re.sub(r"^https?://arxiv\.org/abs/", "", id_url)) if id_url else None
        published = _pick(block, "published")
        year = int(published[:4]) if published else None
        if from_year and year and year < from_year:
            continue
        doi = _pick(block, "arxiv:doi")
        pdf_m = re.search(r'<link[^>]*title="pdf"[^>]*href="([^"]+)"', block, re.I)
        authors = [m.strip() for m in re.findall(r"<name>([\s\S]*?)</name>", block)]
        out.append({
            "source": "arxiv",
            "doi": norm_doi(doi),
            "title": _pick(block, "title") or "",
            "authors": authors,
            "year": year,
            "venue": "arXiv",
            "abstract": _pick(block, "summary"),
            "language": "en",
            "citation_count": 0,
            "is_oa": True,
            "oa_url": pdf_m.group(1) if pdf_m else (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None),
            "landing_url": id_url,
            "ext_ids": {"arxiv": arxiv_id, "doi": norm_doi(doi)},
            "ref_ext_ids": [],
            "relRank": i,
        })
    return out


# ---------- PubMed (E-utilities) ----------
def pubmed(query, from_year, to_year, limit=100):
    esearch = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json"
               f"&retmax={limit}&datetype=pdat&mindate={from_year}&maxdate={to_year}"
               f"&term={quote(query)}")
    s = get_json(esearch, timeout=45)
    ids = (s.get("esearchresult") or {}).get("idlist") or []
    if not ids:
        return []
    sleep(0.4)
    esum = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json"
            f"&id={','.join(ids)}")
    d = get_json(esum, timeout=45)
    r = d.get("result") or {}
    out = []
    for i, uid in enumerate(r.get("uids") or []):
        p = r.get(uid) or {}
        doi = next((a for a in (p.get("articleids") or []) if a.get("idtype") == "doi"), None)
        doi_val = doi.get("value") if doi else None
        out.append({
            "source": "pubmed",
            "doi": norm_doi(doi_val),
            "title": p.get("title") or "",
            "authors": [a.get("name") for a in (p.get("authors") or []) if a.get("name")],
            "year": int(str(p["pubdate"])[:4]) if p.get("pubdate") else None,
            "venue": p.get("fulljournalname") or p.get("source"),
            "abstract": None,
            "language": None,
            "citation_count": 0,
            "is_oa": False,
            "oa_url": None,
            "landing_url": f"https://doi.org/{doi_val}" if doi_val else f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            "ext_ids": {"pmid": uid, "doi": norm_doi(doi_val)},
            "ref_ext_ids": [],
            "relRank": i,
        })
    return out
