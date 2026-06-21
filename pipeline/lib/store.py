"""Reusable DB-write helpers (paper upsert, topic upsert, citations).

Callers are responsible for conn.commit() after a batch of writes.
"""
import json

from .db import now_iso, ROOT
from .slug import unique_slug


def _j(x):
    return json.dumps(x, ensure_ascii=False)


# --- 论文存储布局:一篇一个家 storage/sources/<base>/ ---------------------------
# base = sources.slug;无 slug 时调用方退化为 file_id(id)(沿用全局口径)。
# 一篇论文的 PDF、各版本总结、核查详情全在这个文件夹里。**所有构造这些路径的地方
# 都应走这里**,别再各处写死 "store/pdfs"/"store/summaries"(那是旧两处分离布局)。
def paper_dir(base):
    return ROOT / "storage" / "sources" / base


def pdf_file(base):
    return paper_dir(base) / "paper.pdf"


def summary_file(base, version):
    return paper_dir(base) / f"v{version}.md"


def verify_file(base):
    """核查详情(按版本累积留痕):{"versions": {"1": {verdict, issues, ...}, ...}}。
    与 verify 的【状态】文件(topics/<id>/verified.json 等,喂 daemon)无关、不重叠。"""
    return paper_dir(base) / "verify.json"


def web_source_file(base):
    """web 来源(kind='web':blog/技术报告等)的正文落点,与论文的 paper.pdf 并列。
    抓来的正文存成 markdown;source_path 列指向它。pdf_file 仍管 PDF,两者同在一个家。"""
    return paper_dir(base) / "source.md"


def upsert_paper(conn, p, kind="paper"):
    """Insert a paper if new; otherwise enrich metadata only.
    NEVER touches status / source_path / summarized_at (preserves prior work).
    kind: 'paper'(默认,走 discover/commit 的论文) / 'web'(走 discover_web 的 blog·技术报告)。"""
    existing = conn.execute("SELECT id, sources FROM sources WHERE id=?", (p["id"],)).fetchone()
    ext = _j(p.get("ext_ids") or {})
    refs = _j(p.get("ref_ext_ids") or [])
    authors = _j(p.get("authors") or [])
    srcs = _j(p.get("sources") or [])
    q = p.get("quality") or {}
    q_tier, q_sig = q.get("tier"), ",".join(q.get("signals") or []) or None
    if not existing:
        slug = unique_slug(conn, p["title"], p["id"])
        conn.execute(
            """INSERT INTO sources (id,doi,slug,title,authors,year,venue,abstract,language,citation_count,
                is_oa,oa_url,landing_url,sources,ext_ids,ref_ext_ids,status,is_edge,discovered_at,
                quality_tier,quality_signals,kind)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'discovered', ?, ?, ?, ?, ?)""",
            (p["id"], p.get("doi"), slug, p["title"], authors, p.get("year"), p.get("venue"),
             p.get("abstract"), p.get("language"), p.get("citation_count") or 0,
             1 if p.get("is_oa") else 0, p.get("oa_url"), p.get("landing_url"), srcs, ext, refs,
             1 if p.get("is_edge") else 0, now_iso(), q_tier, q_sig, kind))
        return "new"
    merged_sources = _j(sorted(set(json.loads(existing["sources"] or "[]")) | set(p.get("sources") or [])))
    conn.execute(
        """UPDATE sources SET citation_count=MAX(citation_count,?), is_oa=MAX(is_oa,?),
             oa_url=COALESCE(oa_url,?), abstract=COALESCE(abstract,?), venue=COALESCE(venue,?),
             sources=?, ext_ids=?, quality_tier=COALESCE(?,quality_tier),
             quality_signals=COALESCE(?,quality_signals) WHERE id=?""",
        (p.get("citation_count") or 0, 1 if p.get("is_oa") else 0, p.get("oa_url"),
         p.get("abstract"), p.get("venue"), merged_sources, ext, q_tier, q_sig, p["id"]))
    return "existing"


def upsert_topic(conn, topic, target):
    conn.execute(
        """INSERT INTO topics (id,title,idea,queries,window_years,target,created_at,last_run_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET title=excluded.title, idea=excluded.idea,
             queries=excluded.queries, last_run_at=excluded.last_run_at""",
        (topic["id"], topic.get("title"), topic.get("idea"), _j(topic.get("queries") or []),
         topic.get("window_years") or 20, target, now_iso(), now_iso()))


def set_paper_topic(conn, topic_id, p, rank):
    conn.execute(
        """INSERT INTO source_topic (topic_id,paper_id,relevance,relevance_reason,matched_queries,rank,added_at)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(topic_id,paper_id) DO UPDATE SET relevance=excluded.relevance,
             relevance_reason=excluded.relevance_reason, rank=excluded.rank""",
        (topic_id, p["id"], p.get("relevance"), p.get("relevance_reason"),
         _j(p.get("matched_queries") or []), rank, now_iso()))


def build_citations(conn, sources):
    """Build internal citation edges from OpenAlex referenced_works among the given set."""
    oa_to_id = {}
    for p in sources:
        oa = (p.get("ext_ids") or {}).get("openalex")
        if oa:
            oa_to_id[oa] = p["id"]
    edges = 0
    for p in sources:
        for ref in p.get("ref_ext_ids") or []:
            dst = oa_to_id.get(ref)
            if dst and dst != p["id"]:
                conn.execute("INSERT OR IGNORE INTO citations (src_paper_id,dst_paper_id) VALUES (?,?)",
                             (p["id"], dst))
                edges += 1
    return edges
