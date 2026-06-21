"""Agentic web discovery（只发现，不抓正文）—— 按 topic 联网搜优质 blog/技术报告/X 长贴,
prompt 软判①相关性②内容质量,够格的**直接落库**(kind='web', status='discovered',不打分),
并把这一轮的候选池写进主题状态档(topics/<id>/web_candidates.json + topic_state.json 的 web 段)。

职责切分(对齐论文线):
  - 本脚本 = find 的活:**找哪些 web 值得收**(agent 自己判断,不设数量上限,工具给它)。
  - 抓正文 + 落盘 = fetch 的活:见 `fetch/fetch_web.py`(读 status='discovered' 的 web,
    抓 source.md → source_ready)。`run.py` 的 fetch 阶段会顺带跑它。

agent-first:相关性/质量/收几条全由 claude 软判(ARCHITECTURE §6.5);脚本只做入库+留痕的力气活。
Usage: python3 pipeline/find/discover_web.py <topicId>
"""
import json
import sys
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# --- path shim: 让 `from lib...` 解析到 pipeline/lib,无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.claude import run_claude
from lib.db import open_db, ROOT, now_iso
from lib.log import get_logger, run_log
from lib.topic import load_topic, all_queries, load_state, save_state
from lib import store

log = get_logger("discover_web")

DISCOVER_PROMPT = """你是科研资料策展员。研究方向:
- 主题: {title}
- 想法: {idea}
- 检索方向: {queries}
- 偏好/质量标准: {preferences}

用 WebSearch + WebFetch 找该方向最前沿的优质 **博客 / 技术报告 / 机构 research 文章**
(这类前沿内容常不在 arXiv,如 Anthropic/OpenAI research blog、Lilian Weng、FutureHouse、
distill、各实验室官博,也包括 X(Twitter) 上研究者的高质量长贴)。对每个候选核实,判断两件事:
  ① 相关性:确实命中上面的研究方向?(软判断,够格才收)
  ② 内容质量:作者/机构权威、有实质技术内容,不是营销软文 / 泛科普水文?(软判断)
两条都过才收录。合法公开来源即可。**不设数量上限——把所有真正够格的都收进来**
(宁缺毋滥:不够格的别凑数,但够格的别因为"已经够多了"而漏掉)。

已在库(请勿重复推荐):
{known}

只输出一行严格 JSON 数组(无 markdown 围栏),每个收录项:
[{{"url":"https://...","title":"原文标题","relevance":0-100,"reason":"为何相关且优质,一句话"}}]
没有够格的就输出 []。"""


def parse_items(out):
    i, j = out.find("["), out.rfind("]")
    if i < 0 or j < i:
        return []
    try:
        return json.loads(out[i:j + 1])
    except Exception:
        return []


def norm_url(u):
    """规范化 URL 当主键:剥 utm_*/点击追踪参数 + fragment + 尾斜杠。"""
    pr = urlparse((u or "").strip())
    q = [(k, v) for k, v in parse_qsl(pr.query)
         if not k.startswith("utm_") and k not in ("fbclid", "gclid", "ref", "ref_src")]
    return urlunparse((pr.scheme, pr.netloc, pr.path.rstrip("/"), "", urlencode(q), ""))


def main():
    if len(sys.argv) < 2:
        print("usage: discover_web.py <topicId>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    topic = load_topic(topic_id)
    conn = open_db()
    known = [r[0] for r in conn.execute("SELECT id FROM sources WHERE kind='web'").fetchall()]
    known_block = "\n".join(f"- {u}" for u in known) or "(无)"

    prompt = DISCOVER_PROMPT.format(
        title=topic.get("title") or topic_id, idea=topic.get("idea") or "",
        queries="; ".join(all_queries(topic)[:12]) or "(见想法)",
        preferences=topic.get("preferences") or "权威作者/机构、有实质技术内容",
        known=known_block)
    log.info(f"# web discover: topic={topic_id}, 已在库 web={len(known)}(无上限,agent 自判)")
    out = run_claude(prompt, timeout=900, tools=["WebSearch", "WebFetch"])
    items = parse_items(out)
    log.info(f"  agent 收录候选: {len(items)} 条")

    added = 0
    pool = []  # 写进主题状态档的本轮候选池(留痕)
    for it in items:
        if not isinstance(it, dict) or not it.get("url"):
            continue
        url = norm_url(it["url"])
        if not url:
            continue
        rec = {"url": url, "title": (it.get("title") or url)[:300],
               "relevance": it.get("relevance"), "reason": it.get("reason")}
        pool.append(rec)
        if conn.execute("SELECT 1 FROM sources WHERE id=?", (url,)).fetchone():
            log.info(f"  skip(已在库): {url}")
            continue
        domain = urlparse(url).netloc
        # 直接落库(不打分):身份+元数据入 sources(kind='web', status='discovered'),内容留给 fetch_web 抓。
        p = {"id": url, "title": rec["title"], "doi": None,
             "venue": domain, "language": "en", "sources": ["web", domain],
             "is_oa": True, "oa_url": url, "landing_url": url,
             "relevance": it.get("relevance"), "relevance_reason": it.get("reason"),
             "matched_queries": [], "is_edge": False}
        store.upsert_paper(conn, p, kind="web")   # 默认 status='discovered'
        store.set_paper_topic(conn, topic_id, p, 0)
        conn.commit()
        added += 1
        log.info(f"  + [rel {it.get('relevance')}] {p['title'][:55]}  ({domain})")

    in_db_web = conn.execute(
        """SELECT COUNT(*) FROM sources s JOIN source_topic pt ON pt.paper_id=s.id
            WHERE pt.topic_id=? AND s.kind='web'""", (topic_id,)).fetchone()[0]
    conn.close()

    # 留痕①:本轮候选池 -> topics/<id>/web_candidates.json(对齐论文的 candidates.json)
    d = ROOT / "topics" / topic_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "web_candidates.json").write_text(json.dumps({
        "topic": {"id": topic_id, "title": topic.get("title")},
        "generated_at": now_iso(), "found": len(pool), "newly_added": added,
        "candidates": pool,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    # 留痕②:主题状态档 topic_state.json 加 web 段(每次 discover_web 都更新 → "web 确实更新了"可见)
    st = load_state(topic_id)
    st["web"] = {"last_discover": now_iso(), "in_db": in_db_web,
                 "last_found": len(pool), "last_added": added}
    save_state(topic_id, st)

    log.info(f"\n# web discover done: 本轮候选 {len(pool)}, 新入库 +{added}, "
             f"该主题 web 在库共 {in_db_web}(status=discovered → 待 fetch_web 抓正文)")
    log.info(f"  -> topics/{topic_id}/web_candidates.json + topic_state.json[web]")
    run_log(topic_id, f"discover_web: +{added} web (pool={len(pool)}, in_db={in_db_web})")


if __name__ == "__main__":
    main()
