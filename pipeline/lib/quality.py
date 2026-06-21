"""Hard-signal source quality assessment (no LLM).

Lists live in config/quality/ (editable text files):
  predatory_journals.txt / predatory_publishers.txt  - Beall's-derived, normalized, exact match
  local_blocklist.txt                                - hand-curated additions (newer predators)
  doi_prefix_blocklist.txt                           - DOI prefixes of predatory publishers
  venue_whitelist.txt                                - trusted venues (never blocked)

assess(paper) -> {"tier": "block"|"suspect"|"flag"|"ok"|"trusted", "signals": [...]}
  block   : retracted / DOI-prefix blocklist (确认过的死刑信号)  -> never enters the topic
  suspect : predatory journal/publisher NAME-list hit -> 进库但带标记;
            总结走质疑模式、topic.md 单独标注、未来 RAG 默认降权/过滤
  trusted : whitelisted venue or DOAJ-indexed journal
  flag    : preprint-only / no venue  -> needs higher relevance to enter (commit gate)
  ok      : everything else
"""
import re
import unicodedata
from functools import lru_cache

from .db import ROOT

QUALITY_DIR = ROOT / "config" / "quality"


def norm_name(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"^the ", "", s)


def _load_lines(fname):
    p = QUALITY_DIR / fname
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            out.append(line)
    return out


@lru_cache(maxsize=1)
def _lists():
    return {
        "journals": {norm_name(x) for x in _load_lines("predatory_journals.txt") + _load_lines("local_blocklist.txt")},
        "publishers": {norm_name(x) for x in _load_lines("predatory_publishers.txt")},
        "doi_prefixes": _load_lines("doi_prefix_blocklist.txt"),
        "whitelist": [norm_name(x) for x in _load_lines("venue_whitelist.txt")],
    }


def _whitelisted(venue_norm):
    if not venue_norm:
        return False
    for entry in _lists()["whitelist"]:
        if " " in entry:
            if entry in venue_norm:
                return True
        elif entry == venue_norm:
            return True
    return False


PREPRINT_VENUES = {"arxiv", "biorxiv", "medrxiv", "ssrn", "preprints", "research square", "techrxiv"}


def assess(p):
    """p: dict with (any of) doi, venue, publisher, is_retracted, is_in_doaj, sources.
    Works on both candidates.json entries and sources-table rows (missing keys = unknown)."""
    L = _lists()
    venue_norm = norm_name(p.get("venue"))
    pub_norm = norm_name(p.get("publisher"))
    doi = (p.get("doi") or "").lower()
    signals = []

    trusted = _whitelisted(venue_norm)
    if trusted:
        signals.append("whitelisted_venue")
    if p.get("is_in_doaj"):
        trusted = True
        signals.append("in_doaj")

    # block: 学术界/我们自己确认过的死刑信号,不进库
    if p.get("is_retracted"):
        return {"tier": "block", "signals": signals + ["retracted"]}
    for pre in L["doi_prefixes"]:
        if doi.startswith(pre.lower()):
            return {"tier": "block", "signals": signals + [f"doi_prefix:{pre}"]}

    # suspect: 名单命中(Beall's 有争议条目+全等匹配可能偶撞) -> 进库但带标记;白名单 venue 免疫
    if not _whitelisted(venue_norm):
        if venue_norm and venue_norm in L["journals"]:
            return {"tier": "suspect", "signals": signals + ["predatory_journal"]}
        if pub_norm and pub_norm in L["publishers"]:
            return {"tier": "suspect", "signals": signals + ["predatory_publisher"]}

    if trusted:
        return {"tier": "trusted", "signals": signals}

    # 有正式 DOI(非 arXiv 的 10.48550)的不算纯预印本 —— OpenAlex 常把已发表论文的
    # primary_location 指到 arXiv 版,venue 显示 arXiv 但论文其实过了同行评审
    has_pub_doi = bool(doi) and not doi.startswith("10.48550")
    if not has_pub_doi and (venue_norm in PREPRINT_VENUES or set(p.get("sources") or []) == {"arxiv"}):
        signals.append("preprint_only")
    elif not venue_norm and not has_pub_doi:
        signals.append("no_venue")
    return {"tier": "flag" if signals else "ok", "signals": signals}
