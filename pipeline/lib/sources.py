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
def _openalex_norm(w, i=0):
    """Map one OpenAlex work object -> normalized record. Shared by search + by-id."""
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    oa = w.get("open_access") or {}
    best = w.get("best_oa_location") or {}
    ids = w.get("ids") or {}
    pmid = ids.get("pmid", "").replace("https://pubmed.ncbi.nlm.nih.gov/", "") if ids.get("pmid") else None
    return {
        "source": "openalex",
        "doi": norm_doi(w.get("doi")),
        "title": w.get("display_name") or w.get("title") or "",
        "authors": [a.get("author", {}).get("display_name") for a in (w.get("authorships") or [])
                    if a.get("author", {}).get("display_name")],
        "year": w.get("publication_year"),
        "venue": src.get("display_name"),
        "publisher": src.get("host_organization_name"),
        "is_in_doaj": bool(src.get("is_in_doaj")),
        "is_retracted": bool(w.get("is_retracted")),
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
    }


def openalex(query, from_date, per_page=120):
    url = (f"https://api.openalex.org/works?search={quote(query)}"
           f"&filter=from_publication_date:{from_date}"
           f"&per-page={per_page}&sort=relevance_score:desc&mailto={MAILTO}")
    data = get_json(url, timeout=45)
    return [_openalex_norm(w, i) for i, w in enumerate(data.get("results") or [])]


def openalex_by_id(ident):
    """Single-work lookup. ident must be OpenAlex-acceptable: 'doi:10.x' / 'W123' /
    'pmid:123' / 'openalex:W123'. Returns one normalized record, or None if not found."""
    url = f"https://api.openalex.org/works/{quote(ident, safe=':/')}?mailto={MAILTO}"
    try:
        data = get_json(url, timeout=45)
    except HttpError:
        return None
    return _openalex_norm(data) if data.get("id") else None


# ---------- Semantic Scholar ----------
_SS_FIELDS = "title,abstract,year,authors,venue,externalIds,citationCount,openAccessPdf,publicationTypes"


def _ss_norm(p, i=0):
    """Map one Semantic Scholar paper object -> normalized record. Shared by search + by-id."""
    ext = p.get("externalIds") or {}
    oapdf = p.get("openAccessPdf") or {}
    return {
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
    }


def semantic_scholar(query, from_year, limit=100):
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}"
           f"&year={from_year}-&fields={_SS_FIELDS}&limit={limit}")
    try:
        data = get_json(url, timeout=45, retries=3, retry_delay=3)
    except HttpError as e:
        if e.status == 429:
            return []  # rate-limited without a key; skip gracefully
        raise
    return [_ss_norm(p, i) for i, p in enumerate(data.get("data") or [])]


def semantic_scholar_by_id(ident):
    """Single-paper lookup. ident like 'DOI:10.x' / 'arXiv:2404.16130' / '<s2 paperId>'.
    Returns one normalized record, or None (incl. graceful skip on 429 without a key)."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{quote(ident, safe=':')}?fields={_SS_FIELDS}"
    try:
        data = get_json(url, timeout=45, retries=2, retry_delay=3)
    except HttpError:
        return None
    return _ss_norm(data) if data.get("paperId") else None


# ---------- arXiv (Atom XML, parsed with regex) ----------
def _pick(block, tag):
    m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", block, re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def _arxiv_blocks(xml):
    return ["<entry>" + part.split("</entry>")[0] for part in xml.split("<entry>")[1:]]


def _arxiv_norm(block, i=0):
    """Map one arXiv Atom <entry> block -> normalized record. Shared by search + by-id."""
    id_url = _pick(block, "id")
    arxiv_id = re.sub(r"v\d+$", "", re.sub(r"^https?://arxiv\.org/abs/", "", id_url)) if id_url else None
    published = _pick(block, "published")
    year = int(published[:4]) if published else None
    doi = _pick(block, "arxiv:doi")
    pdf_m = re.search(r'<link[^>]*title="pdf"[^>]*href="([^"]+)"', block, re.I)
    authors = [m.strip() for m in re.findall(r"<name>([\s\S]*?)</name>", block)]
    return {
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
    }


def arxiv(query, from_year, limit=80):
    url = (f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}"
           f"&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending")
    xml = get_text(url, timeout=45)
    out = []
    for i, block in enumerate(_arxiv_blocks(xml)):
        rec = _arxiv_norm(block, i)
        if from_year and rec["year"] and rec["year"] < from_year:
            continue
        out.append(rec)
    return out


def arxiv_by_id(arxiv_id):
    """Single-paper lookup via the arXiv API id_list. Returns one normalized record or None."""
    aid = re.sub(r"v\d+$", "", str(arxiv_id).strip())
    xml = get_text(f"https://export.arxiv.org/api/query?id_list={quote(aid)}", timeout=45)
    blocks = _arxiv_blocks(xml)
    if not blocks:
        return None
    rec = _arxiv_norm(blocks[0])
    title = (rec.get("title") or "").strip()
    return rec if title and not title.lower().startswith("error") else None


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


# ---------- By-id seeding (point-name a paper, bypass keyword search) ----------
_ARXIV_NEW = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_ARXIV_OLD = re.compile(r"^[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$", re.I)


def parse_ident(raw):
    """Classify a user-supplied identifier into (kind, value).
    kind ∈ {doi, arxiv, openalex, pmid, unknown}. Tolerant of URLs and prefixes."""
    s = (raw or "").strip()
    low = s.lower()
    if low.startswith("http"):
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([a-z\-]+/\d{7}|\d{4}\.\d{4,5})(v\d+)?", low)
        if m:
            return ("arxiv", m.group(1))
        m = re.search(r"doi\.org/(10\.[^\s?#]+)", low)
        if m:
            return ("doi", m.group(1))
        m = re.search(r"openalex\.org/(W\d+)", s, re.I)
        if m:
            return ("openalex", m.group(1).upper())
        return ("unknown", s)
    if low.startswith("arxiv:"):
        return ("arxiv", re.sub(r"v\d+$", "", s[6:].strip()))
    if low.startswith("doi:"):
        return ("doi", s[4:].strip())
    if low.startswith("pmid:"):
        return ("pmid", s[5:].strip())
    if re.match(r"^W\d+$", s):
        return ("openalex", s)
    if low.startswith("10."):
        return ("doi", s)
    if _ARXIV_NEW.match(s) or _ARXIV_OLD.match(s):
        return ("arxiv", re.sub(r"v\d+$", "", s))
    if s.isdigit():
        return ("pmid", s)
    return ("unknown", s)


def fetch_by_id(raw):
    """Fetch one paper's metadata by DOI / arxiv id / OpenAlex id / PMID / URL.
    Returns a normalized record (same shape as the search clients) or None.
    Source priority favors richest metadata (OpenAlex: abstract+refs+OA) per id kind."""
    kind, val = parse_ident(raw)
    if kind == "doi":
        return openalex_by_id(f"doi:{norm_doi(val)}") or semantic_scholar_by_id(f"DOI:{norm_doi(val)}")
    if kind == "arxiv":
        # OpenAlex usually lacks arxiv-only preprints; arxiv API is the reliable primary.
        return arxiv_by_id(val) or semantic_scholar_by_id(f"arXiv:{val}")
    if kind == "openalex":
        return openalex_by_id(val)
    if kind == "pmid":
        return openalex_by_id(f"pmid:{val}") or semantic_scholar_by_id(f"PMID:{val}")
    # unknown: best-effort probe (DOI shape first, then arxiv)
    return openalex_by_id(f"doi:{val}") or arxiv_by_id(val) or semantic_scholar_by_id(val)
