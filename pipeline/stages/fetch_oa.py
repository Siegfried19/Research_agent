"""Phase 2: download open-access PDFs for a topic's selected papers.
Usage: python3 pipeline/stages/fetch_oa.py <topicId|all>
PDF 是唯一原文来源(总结/核查都直读 PDF);不再抽存 store/text 文本(2026-06-16 移除)。
"""
import json
import re
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT, load_config, now_iso
from lib.http import download_pdf, sleep, HttpError
from lib.log import get_logger, run_log
from lib.slug import file_id

config = load_config()
PDF_DIR = ROOT / config["paths"]["pdfs"]
log = get_logger("fetch_oa")


def urls_for(r):
    urls = []
    if r["oa_url"]:
        urls.append(r["oa_url"])
    arxiv_id = None
    try:
        arxiv_id = json.loads(r["ext_ids"] or "{}").get("arxiv")
    except Exception:
        pass
    if not arxiv_id and r["id"].startswith("arxiv:"):
        arxiv_id = r["id"][6:]
    if arxiv_id:
        ax = f"https://arxiv.org/pdf/{re.sub(r'v[0-9]+$', '', str(arxiv_id))}"
        if ax not in urls:
            urls.append(ax)
    return urls


def main():
    if len(sys.argv) < 2:
        print("usage: fetch_oa.py <topicId|all>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    conn = open_db()
    if topic_id == "all":
        rows = conn.execute(
            "SELECT * FROM papers WHERE is_oa=1 AND oa_url IS NOT NULL AND status='discovered'").fetchall()
    else:
        rows = conn.execute(
            """SELECT p.* FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                WHERE pt.topic_id=? AND p.is_oa=1 AND p.oa_url IS NOT NULL AND p.status='discovered'
                ORDER BY pt.rank""", (topic_id,)).fetchall()

    log.info(f"# OA download: {len(rows)} candidates")
    ua = config["download"]["user_agent"]
    timeout = config["download"]["timeout_ms"] / 1000
    ok = fail = 0
    for r in rows:
        base = r["slug"] or file_id(r["id"])
        pdf_path = PDF_DIR / (base + ".pdf")
        bytes_, last_err = None, None
        for u in urls_for(r):
            try:
                bytes_ = download_pdf(u, pdf_path, ua, timeout)
                break
            except (HttpError, Exception) as e:  # noqa: BLE001
                last_err = e
        if bytes_ is None:
            conn.execute("UPDATE papers SET pdf_path=NULL, status='pdf_failed', pdf_fetched_at=? WHERE id=?",
                         (now_iso(), r["id"]))
            fail += 1
            log.info(f"  FAIL [{last_err}] {(r['title'] or '')[:50]}")
        else:
            conn.execute("UPDATE papers SET pdf_path=?, status='pdf_downloaded', pdf_fetched_at=? WHERE id=?",
                         (str(pdf_path.relative_to(ROOT)), now_iso(), r["id"]))
            ok += 1
            log.info(f"  OK   [{bytes_ // 1024}KB] {(r['title'] or '')[:55]}")
        conn.commit()
        sleep(config["download"]["delay_ms"] / 1000)
    conn.close()
    log.info(f"\n# Done: {ok} pdf, {fail} failed")
    run_log(topic_id, f"fetch_oa: {ok} pdf, {fail} failed")


if __name__ == "__main__":
    main()
