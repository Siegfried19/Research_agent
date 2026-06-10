"""Recover free full text for papers we missed, WITHOUT any login.
Per paper lacking a PDF, try (in order): arXiv by id, Unpaywall (repository/arXiv
locations BEFORE publisher — publisher PDFs often 403), arXiv by title, then
conference-run OA sites via DBLP title search (PMLR/ACL Anthology/OpenReview).
Usage: python3 pipeline/recover_oa.py <topicId|all>

Fixes the old bug: it used to take Unpaywall's best_oa_location first (usually the
publisher PDF -> 403) and only matched arXiv by exact title (fails on titles that
OpenAlex truncated to e.g. "ASE"/"AMP").
"""
import json
import re
import subprocess
import sys
from urllib.parse import quote

from lib.db import open_db, ROOT, load_config, now_iso
from lib.http import get_json, get_text, download_pdf, sleep
from lib.merge import norm_title
from lib.log import get_logger, run_log

config = load_config()
PDF_DIR = ROOT / config["paths"]["pdfs"]
TXT_DIR = ROOT / "store" / "text"
MAIL = "a0904251001@gmail.com"
log = get_logger("recover_oa")


def arxiv_id_of(r):
    try:
        ax = json.loads(r["ext_ids"] or "{}").get("arxiv")
        if ax:
            return re.sub(r"v[0-9]+$", "", str(ax))
    except Exception:
        pass
    if r["id"].startswith("arxiv:"):
        return re.sub(r"v[0-9]+$", "", r["id"][6:])
    return None


def unpaywall_pdfs(doi):
    """Return candidate PDF urls, repository/arXiv-hosted FIRST, publisher last."""
    try:
        d = get_json(f"https://api.unpaywall.org/v2/{doi}?email={MAIL}", timeout=30)
    except Exception:
        return []
    locs = [d.get("best_oa_location")] + (d.get("oa_locations") or [])
    locs = [l for l in locs if l]
    repo = [l["url_for_pdf"] for l in locs if l.get("url_for_pdf") and l.get("host_type") != "publisher"]
    pub = [l["url_for_pdf"] for l in locs if l.get("url_for_pdf") and l.get("host_type") == "publisher"]
    seen, out = set(), []
    for u in repo + pub:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def arxiv_pdf_candidates(ax):
    """Candidate arXiv PDF urls, most-likely first. arXiv is quirky: the bare
    /pdf/<id> path sometimes 404s, and even the 'latest' version can 404 while an
    earlier one serves (e.g. 2211.15205: bare & v2 404, only v1 works). So we
    enumerate bare + v1..v<latest> and let the download loop pick whichever is a
    real PDF."""
    ax = re.sub(r"v[0-9]+$", "", ax)  # strip any version we were handed
    latest = 0
    try:
        xml = get_text(f"http://export.arxiv.org/api/query?id_list={ax}", timeout=30)
        ent = xml.split("<entry>")[1] if "<entry>" in xml else ""
        m = re.search(r"<id>https?://arxiv\.org/abs/[^<]*v([0-9]+)</id>", ent, re.I)
        if m:
            latest = int(m.group(1))
    except Exception:
        pass
    vers = list(range(1, latest + 1)) if latest else [1, 2, 3]
    return [f"https://arxiv.org/pdf/{ax}"] + [f"https://arxiv.org/pdf/{ax}v{i}" for i in vers]


def arxiv_pdf_by_title(title):
    try:
        xml = get_text(
            f"https://export.arxiv.org/api/query?search_query=ti:%22{quote(title[:120])}%22&max_results=3",
            timeout=30)
    except Exception:
        return None
    for e in xml.split("<entry>")[1:]:
        t = (re.search(r"<title>([\s\S]*?)</title>", e, re.I) or [None, ""])[1]
        idm = re.search(r"<id>([\s\S]*?)</id>", e, re.I)
        # Keep the version suffix — bare ids sometimes 404 (see arxiv_versioned_url).
        if idm and norm_title(t) == norm_title(title):
            vid = re.sub(r"^https?://arxiv\.org/abs/", "", idm.group(1)).strip()
            if vid:
                return f"https://arxiv.org/pdf/{vid}"
    return None


def proceedings_pdf_by_title(title):
    """Conference-run OA sites (PMLR / ACL Anthology / OpenReview), found via DBLP
    title search. Covers papers with no DOI and no arXiv (e.g. ICML on PMLR)."""
    try:
        d = get_json(f"https://dblp.org/search/publ/api?q={quote(title[:120])}&format=json&h=5",
                     timeout=30)
    except Exception:
        return None
    hits = (((d.get("result") or {}).get("hits") or {}).get("hit")) or []
    for h in hits:
        info = h.get("info") or {}
        if norm_title(info.get("title") or "") != norm_title(title):
            continue
        ees = info.get("ee") or []
        for ee in [ees] if isinstance(ees, str) else ees:
            m = re.match(r"https?://proceedings\.mlr\.press/(v\d+)/([^/.]+)\.html", ee)
            if m:
                return f"https://proceedings.mlr.press/{m.group(1)}/{m.group(2)}/{m.group(2)}.pdf"
            m = re.match(r"https?://aclanthology\.org/([^/?#]+?)/?$", ee)
            if m:
                return f"https://aclanthology.org/{m.group(1)}.pdf"
            m = re.match(r"https?://openreview\.net/forum\?id=([^&]+)", ee)
            if m:
                return f"https://openreview.net/pdf?id={m.group(1)}"
    return None


def candidate_urls(r):
    urls, vias = [], []
    ax = arxiv_id_of(r)
    if ax:
        for u in arxiv_pdf_candidates(ax):
            urls.append(u); vias.append("arxiv-id")
    if r["doi"]:
        for u in unpaywall_pdfs(r["doi"]):
            urls.append(u); vias.append("unpaywall")
    bt = arxiv_pdf_by_title(r["title"]) if r["title"] else None
    if bt and bt not in urls:
        urls.append(bt); vias.append("arxiv-title")
    pp = proceedings_pdf_by_title(r["title"]) if r["title"] else None
    if pp and pp not in urls:
        urls.append(pp); vias.append("dblp-oa")
    return list(zip(urls, vias))


def extract_text(pdf_path, txt_path):
    try:
        subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", str(pdf_path), str(txt_path)],
                       timeout=60, check=False)
        if txt_path.exists() and txt_path.stat().st_size > 200:
            return str(txt_path.relative_to(ROOT))
    except Exception:
        pass
    return None


def main():
    topic_id = sys.argv[1] if len(sys.argv) > 1 else "all"
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    conn = open_db()
    if topic_id == "all":
        rows = conn.execute(
            "SELECT * FROM papers WHERE pdf_path IS NULL AND status IN ('pdf_failed','discovered')").fetchall()
    else:
        rows = conn.execute(
            """SELECT p.* FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                WHERE pt.topic_id=? AND p.pdf_path IS NULL AND p.status IN ('pdf_failed','discovered')
                ORDER BY pt.rank""", (topic_id,)).fetchall()

    log.info(f"# Recover free OA: {len(rows)} papers lacking full text")
    timeout = config["download"]["timeout_ms"] / 1000
    recovered = 0
    for r in rows:
        base = r["slug"] or re.sub(r"[^a-z0-9._-]", "_", r["id"], flags=re.I)[:180]
        pdf_path = PDF_DIR / (base + ".pdf")
        txt_path = TXT_DIR / (base + ".txt")
        cands = candidate_urls(r)
        if not cands:
            log.info(f"  --   no free source: {(r['title'] or '')[:50]}")
            sleep(0.5)
            continue
        done = False
        for url, via in cands:
            try:
                bytes_ = download_pdf(url, pdf_path, config["download"]["user_agent"], timeout)
                tpath = extract_text(pdf_path, txt_path)
                conn.execute("UPDATE papers SET pdf_path=?, text_path=?, status='pdf_downloaded', pdf_fetched_at=? WHERE id=?",
                             (str(pdf_path.relative_to(ROOT)), tpath, now_iso(), r["id"]))
                conn.commit()
                recovered += 1
                log.info(f"  OK [{via}, {bytes_ // 1024}KB] {(r['title'] or '')[:48]}")
                done = True
                break
            except Exception as e:  # noqa: BLE001
                last = f"{via}: {e}"
        if not done:
            log.info(f"  FAIL [{last}] {(r['title'] or '')[:44]}")
        sleep(config["download"]["delay_ms"] / 1000)
    conn.close()
    log.info(f"\n# Recovered {recovered}/{len(rows)} for free. (rest -> Tier B paywall)")
    run_log(topic_id, f"recover_oa: {recovered}/{len(rows)} recovered free")


if __name__ == "__main__":
    main()
