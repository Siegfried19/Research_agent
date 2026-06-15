"""Agentic free-source hunt: for papers STILL lacking full text after recover_oa's
rule-based channels, ask headless Claude (with web search) to find a legitimate
free PDF url. The script (not the agent) downloads, validates %PDF, extracts text
and updates the DB. Whatever still fails goes on to Tier B — this stage exists to
spend a cheap web-searching agent before the expensive browser+OpenAthens path.
Usage: python3 pipeline/stages/recover_agent.py <topicId|all> [concurrency]
"""
import json
import re
import subprocess
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.claude import run_claude, pool
from lib.db import open_db, ROOT, load_config, now_iso
from lib.http import download_pdf
from lib.merge import title_matches
from lib.log import get_logger, run_log

config = load_config()
PDF_DIR = ROOT / config["paths"]["pdfs"]
TXT_DIR = ROOT / "store" / "text"
log = get_logger("recover_agent")

PROMPT = """你是论文全文猎手。任务：为下面这篇论文找一个**合法的免费全文 PDF 直链**。

论文元数据：
- 标题: {title}
- 作者: {authors}
- 年份: {year}  期刊/会议: {venue}
- DOI: {doi}
- 落地页: {landing}

用 WebSearch 搜索、用 WebFetch 打开候选页面核实。合法来源包括：作者个人主页、
大学/机构知识库、实验室网站、会议官网（如 PMLR/ACL/OpenReview/CVF）、政府或
基金会报告库、preprint 服务器。
绝对禁止：Sci-Hub/LibGen 等盗版镜像站、任何绕过付费墙的途径、需要登录的链接。
链接必须直接指向 PDF 文件本身（不是摘要页）。核实标题与作者确实匹配这篇论文，
拿不准就算找不到。找不到是正常结果，不要硬凑。

只输出一行严格 JSON（无 markdown 围栏）：
{{"url": "https://...pdf" 或 null, "source": "一句话说明来源", "confidence": "high|medium|low"}}"""


def parse_verdict(out):
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j < i:
        raise ValueError("no JSON object in output")
    return json.loads(out[i:j + 1])


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
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 2
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
    if not rows:
        log.info("# Agent hunt: nothing lacking full text — skip")
        run_log(topic_id, "recover_agent: 0 papers to hunt")
        conn.close()
        return

    log.info(f"# Agent hunt: {len(rows)} papers, concurrency={concurrency}")
    timeout = config["download"]["timeout_ms"] / 1000

    def hunt(r, i):
        authors = ", ".join(json.loads(r["authors"] or "[]")[:6])
        prompt = PROMPT.format(title=r["title"], authors=authors or "?", year=r["year"] or "?",
                               venue=r["venue"] or "?", doi=r["doi"] or "无",
                               landing=r["landing_url"] or "无")
        out = run_claude(prompt, timeout=600, tools=["WebSearch", "WebFetch"])
        return parse_verdict(out)

    verdicts = pool(rows, hunt, limit=concurrency)
    found = 0
    for r, v in zip(rows, verdicts):
        title = (r["title"] or "")[:48]
        if not isinstance(v, dict) or v.get("error"):
            log.info(f"  ERR  [{(v or {}).get('error', 'no verdict')[:60]}] {title}")
            continue
        if not v.get("url"):
            log.info(f"  --   agent found nothing: {title}")
            continue
        base = r["slug"] or re.sub(r"[^a-z0-9._-]", "_", r["id"], flags=re.I)[:180]
        pdf_path = PDF_DIR / (base + ".pdf")
        txt_path = TXT_DIR / (base + ".txt")
        try:
            bytes_ = download_pdf(v["url"], pdf_path, config["download"]["user_agent"], timeout)
        except Exception as e:  # noqa: BLE001
            log.info(f"  FAIL [agent url no good: {e}] {title}")
            continue
        tpath = extract_text(pdf_path, txt_path)
        # 张冠李戴防线:agent 可能给了"真实有效但属于另一篇"的 PDF —— %PDF 校验挡不住,
        # 这里用标题核对兜底(抽得出文本才能核;没文本则放过,反正总结阶段会因无文本跳过)。
        if tpath:
            text = txt_path.read_text(encoding="utf-8", errors="ignore")
            if not title_matches(r["title"], text):
                pdf_path.unlink(missing_ok=True)
                txt_path.unlink(missing_ok=True)
                log.info(f"  REJECT [疑似张冠李戴:正文与标题不匹配] {title}")
                continue
        conn.execute("UPDATE papers SET pdf_path=?, text_path=?, oa_url=COALESCE(oa_url,?), "
                     "status='pdf_downloaded', pdf_fetched_at=? WHERE id=?",
                     (str(pdf_path.relative_to(ROOT)), tpath, v["url"], now_iso(), r["id"]))
        conn.commit()
        found += 1
        log.info(f"  OK   [{v.get('confidence')}, {bytes_ // 1024}KB, {(v.get('source') or '')[:40]}] {title}")
    conn.close()
    log.info(f"\n# Agent recovered {found}/{len(rows)}. (rest -> Tier B paywall)")
    run_log(topic_id, f"recover_agent: {found}/{len(rows)} found by web-searching agent")


if __name__ == "__main__":
    main()
