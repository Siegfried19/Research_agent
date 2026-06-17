"""Retroactive quality audit of papers already committed to a topic.

Fetches fresh OpenAlex metadata by DOI (is_retracted / is_in_doaj / publisher),
runs lib.quality.assess on every paper, writes topics/<id>/quality_audit.md.
Default is dry-run (report only); --apply removes block-tier papers from the
topic (and from papers/citations if no other topic references them) and
recomputes rank, mirroring commit.py.

Usage: python3 pipeline/tools/audit_quality.py <topicId> [--apply] [--no-fetch]
"""
import json
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT, now_iso
from lib.http import get_json, sleep
from lib.log import get_logger, run_log
from lib import quality

log = get_logger("audit")
MAILTO = "a0904251001@gmail.com"


def fetch_openalex_meta(dois):
    """Batch-fetch OpenAlex works by DOI (50 per call). Returns {doi: meta}."""
    out = {}
    dois = [d for d in dois if d and d.startswith("10.")]
    for i in range(0, len(dois), 50):
        chunk = dois[i:i + 50]
        url = (f"https://api.openalex.org/works?filter=doi:{'|'.join(chunk)}"
               f"&per-page=50&mailto={MAILTO}")
        try:
            data = get_json(url, timeout=45)
        except Exception as e:  # noqa: BLE001
            log.info(f"  openalex batch {i} failed: {e}")
            continue
        for w in data.get("results") or []:
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            src = (w.get("primary_location") or {}).get("source") or {}
            out[doi] = {
                "is_retracted": bool(w.get("is_retracted")),
                "is_in_doaj": bool(src.get("is_in_doaj")),
                "publisher": src.get("host_organization_name"),
                "venue": src.get("display_name"),
            }
        sleep(0.5)
    return out


def remove_papers(conn, topic_id, paper_ids):
    """Remove papers from a topic; delete orphans (no other topic) + their citation edges."""
    removed_files = []
    for pid in paper_ids:
        conn.execute("DELETE FROM paper_topic WHERE topic_id=? AND paper_id=?", (topic_id, pid))
        other = conn.execute("SELECT COUNT(*) c FROM paper_topic WHERE paper_id=?", (pid,)).fetchone()["c"]
        if other == 0:
            row = conn.execute("SELECT pdf_path FROM papers WHERE id=?", (pid,)).fetchone()
            if row and row["pdf_path"]:
                removed_files.append(row["pdf_path"])
            conn.execute("DELETE FROM citations WHERE src_paper_id=? OR dst_paper_id=?", (pid, pid))
            conn.execute("DELETE FROM summary_versions WHERE paper_id=?", (pid,))
            conn.execute("DELETE FROM papers WHERE id=?", (pid,))
    rows = conn.execute(
        """SELECT pt.paper_id FROM paper_topic pt JOIN papers p ON p.id=pt.paper_id
            WHERE pt.topic_id=? ORDER BY pt.relevance DESC, p.citation_count DESC""", (topic_id,)).fetchall()
    for i, r in enumerate(rows):
        conn.execute("UPDATE paper_topic SET rank=? WHERE topic_id=? AND paper_id=?",
                     (i + 1, topic_id, r["paper_id"]))
    return removed_files


def main():
    if len(sys.argv) < 2:
        print("usage: audit_quality.py <topicId> [--apply] [--no-fetch]", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    apply_mode = "--apply" in sys.argv
    no_fetch = "--no-fetch" in sys.argv

    conn = open_db()
    rows = [dict(r) for r in conn.execute(
        """SELECT p.*, pt.relevance, pt.rank FROM papers p
            JOIN paper_topic pt ON pt.paper_id=p.id
           WHERE pt.topic_id=? ORDER BY pt.rank""", (topic_id,)).fetchall()]
    if not rows:
        log.info(f"no papers for topic {topic_id}")
        return

    meta = {} if no_fetch else fetch_openalex_meta([r.get("doi") for r in rows])
    log.info(f"audit_quality: {len(rows)} papers, openalex meta for {len(meta)}")

    verdicts = []
    for r in rows:
        m = meta.get((r.get("doi") or "").lower(), {})
        p = {**r, **{k: v for k, v in m.items() if v},
             "is_retracted": m.get("is_retracted", False),
             "is_in_doaj": m.get("is_in_doaj", False),
             "sources": json.loads(r.get("sources") or "[]")}
        verdicts.append((r, quality.assess(p)))

    # verdict 回写 papers 表(quality_tier/quality_signals),下游(总结/渲染/RAG)按标记行事
    for r, q in verdicts:
        conn.execute("UPDATE papers SET quality_tier=?, quality_signals=? WHERE id=?",
                     (q["tier"], ",".join(q["signals"]) or None, r["id"]))
    conn.commit()

    by_tier = {}
    for r, q in verdicts:
        by_tier.setdefault(q["tier"], []).append((r, q))
    blocked = by_tier.get("block", [])
    suspect = by_tier.get("suspect", [])
    flagged = by_tier.get("flag", [])

    lines = [f"# Quality audit — {topic_id}", f"_generated: {now_iso()}  papers: {len(rows)}  "
             f"block: {len(blocked)}  suspect: {len(suspect)}  flag: {len(flagged)}  "
             f"trusted: {len(by_tier.get('trusted', []))}  ok: {len(by_tier.get('ok', []))}_", ""]
    for tier, label in (("block", "🚫 BLOCK(建议移除)"),
                        ("suspect", "🟡 SUSPECT(掠夺名单命中,带标记入库,总结走质疑模式)"),
                        ("flag", "⚠️ FLAG(人工瞄一眼)")):
        if by_tier.get(tier):
            lines.append(f"## {label}")
            for r, q in by_tier[tier]:
                lines.append(f"- [{','.join(q['signals'])}] rel={r['relevance']:.0f} rank={r['rank']} "
                             f"`{r['id']}` {r['title'][:90]}  ({r.get('venue') or '-'})")
            lines.append("")

    report = ROOT / "topics" / topic_id / "quality_audit.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"  -> {report.relative_to(ROOT)}")
    for r, q in blocked:
        log.info(f"  BLOCK   [{','.join(q['signals'])}] {r['title'][:70]}")
    for r, q in suspect:
        log.info(f"  SUSPECT [{','.join(q['signals'])}] {r['title'][:70]}")
    for r, q in flagged:
        log.info(f"  FLAG    [{','.join(q['signals'])}] {r['title'][:70]}")

    if apply_mode and blocked:
        files = remove_papers(conn, topic_id, [r["id"] for r, _ in blocked])
        conn.commit()
        log.info(f"  APPLIED: removed {len(blocked)} papers, rank recomputed")
        if files:
            log.info("  orphaned files (left on disk): " + ", ".join(files))
    elif blocked:
        log.info(f"  dry-run: {len(blocked)} 篇建议移除,跑 --apply 执行")
    conn.close()
    run_log(topic_id, f"audit_quality: block={len(blocked)} suspect={len(suspect)} flag={len(flagged)} "
                      f"applied={'yes' if apply_mode and blocked else 'no'}")


if __name__ == "__main__":
    main()
