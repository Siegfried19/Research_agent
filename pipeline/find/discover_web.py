"""Agentic web discovery —— 按 topic 联网搜优质 blog/技术报告,prompt 软判①相关性②内容质量,
收录的抓正文成 markdown 入库(kind='web')。复用 hunt 的 agent 联网外壳 + commit 的入库出口
(store.upsert_paper/set_paper_topic);不打分(score)、不总结(worklist 按 kind!='web' 排除)。

两阶段:①发现+软判 一次 run_claude 出收录清单;②逐条抓正文——**抓取工具箱交给 agent 自己挑**:
静态页 WebFetch / 动态页·X·登录墙 用真 Chrome(Bash 跑 opencli browser open+screenshot,再 Read 截图)。
"怎么抓、怎么看"由 claude 自己决定;脚本只管 Chrome 起停+独占锁(力气活,防越开越多)。
设 WEB_NO_CHROME=1 可强制纯静态(不起 Chrome)。

Usage: python3 pipeline/find/discover_web.py <topicId> [max_n]
"""
import json
import os
import sys
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# --- path shim: 让 `from lib...` 解析到 pipeline/lib,无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.claude import run_claude
from lib.db import open_db, ROOT, now_iso
from lib.log import get_logger, run_log
from lib.store import web_source_file
from lib.topic import load_topic, all_queries
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
两条都过才收录。合法公开来源即可。

已在库(请勿重复推荐):
{known}

只输出一行严格 JSON 数组(无 markdown 围栏),每个收录项:
[{{"url":"https://...","title":"原文标题","relevance":0-100,"reason":"为何相关且优质,一句话"}}]
没有够格的就输出 []。最多 {max_n} 条。"""

# 抓正文:把工具箱摆给 agent,怎么抓/怎么看它自己定(不替它写死判断)。
FETCH_PROMPT = """把这个网址的正文提取成干净 markdown:
{url}

自己挑工具(按页面类型判断,不必问):
- **静态页**(博客 / 文档 / 官网文章): 直接用 WebFetch。
{chrome_section}

去掉导航/广告/页脚/评论,保留标题、正文、代码块、列表、表格。
只输出 markdown 正文本身,不要任何额外说明或围栏。抓不到就只输出一行: FAILED"""


def _chrome_section(url, alias, shot, chrome_ok):
    if not chrome_ok:
        return "- (本机当前只有 WebFetch;动态/登录页抓不动就输出 FAILED)"
    prof = f"--profile {alias} " if alias else ""
    return (
        "- **动态页 / X(Twitter) / 登录墙 / JS 重的页面**: WebFetch 抓不动,改用真 Chrome\n"
        "  (已登录,通过 Bash 跑 opencli):\n"
        f'      opencli {prof}browser tierb open "{url}"\n'
        f"      opencli {prof}browser tierb screenshot {shot}\n"
        f"  然后用 Read 读 {shot} 这张截图、把正文/帖子内容提取成 markdown。\n"
        f"  (纯文字页也可试 `opencli {prof}browser tierb extract` 直接抓 DOM 文本。)"
    )


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


def start_chrome():
    """尽量起真 Chrome(复用 fetch_tierb 的生命周期:独占锁 + ensure)。
    返回 (chrome_ok, alias, lock_fp, tb_module)。起不来就降级 (False, ...)。"""
    if os.environ.get("WEB_NO_CHROME"):
        return False, None, None, None
    try:
        import fetch.fetch_tierb as tb
        lock_fp = tb.chrome_lock()
        tb.ensure_chrome()
        log.info(f"  真 Chrome 就绪(profile {tb.ALIAS}) —— agent 可抓动态页/X")
        return True, tb.ALIAS, lock_fp, tb
    except Exception as e:  # noqa: BLE001
        log.info(f"  真 Chrome 不可用,降级纯静态抓取: {e}")
        return False, None, None, None


def main():
    if len(sys.argv) < 2:
        print("usage: discover_web.py <topicId> [max_n]", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    max_n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    topic = load_topic(topic_id)
    conn = open_db()
    known = [r[0] for r in conn.execute("SELECT id FROM sources WHERE kind='web'").fetchall()]
    known_block = "\n".join(f"- {u}" for u in known) or "(无)"

    prompt = DISCOVER_PROMPT.format(
        title=topic.get("title") or topic_id, idea=topic.get("idea") or "",
        queries="; ".join(all_queries(topic)[:12]) or "(见想法)",
        preferences=topic.get("preferences") or "权威作者/机构、有实质技术内容",
        known=known_block, max_n=max_n)
    log.info(f"# web discover: topic={topic_id}, 已在库 web={len(known)}")
    out = run_claude(prompt, timeout=900, tools=["WebSearch", "WebFetch"])
    items = parse_items(out)
    log.info(f"  agent 收录候选: {len(items)} 条")

    chrome_ok, alias, lock_fp, tb = start_chrome()
    added = 0
    try:
        for i, it in enumerate(items):
            if not isinstance(it, dict) or not it.get("url"):
                continue
            url = norm_url(it["url"])
            if not url:
                continue
            if conn.execute("SELECT 1 FROM sources WHERE id=?", (url,)).fetchone():
                log.info(f"  skip(已在库): {url}")
                continue
            # 阶段2:抓正文 —— 工具箱给 agent,怎么抓/怎么看它自己定
            shot = ROOT / "storage" / "dl_tmp" / f"web_shot_{i}.png"
            shot.parent.mkdir(parents=True, exist_ok=True)
            sec = _chrome_section(url, alias, shot, chrome_ok)
            tools = ["WebFetch", "Bash", "Read"] if chrome_ok else ["WebFetch"]
            md = run_claude(FETCH_PROMPT.format(url=url, chrome_section=sec), timeout=600, tools=tools)
            if not md or md.strip() == "FAILED" or len(md.strip()) < 200:
                log.info(f"  skip(抓取失败/过短): {url}")
                continue
            domain = urlparse(url).netloc
            p = {"id": url, "title": (it.get("title") or url)[:300], "doi": None,
                 "venue": domain, "language": "en", "sources": ["web", domain],
                 "is_oa": True, "oa_url": url, "landing_url": url,
                 "relevance": it.get("relevance"), "relevance_reason": it.get("reason"),
                 "matched_queries": [], "is_edge": False}
            store.upsert_paper(conn, p, kind="web")
            slug = conn.execute("SELECT slug FROM sources WHERE id=?", (url,)).fetchone()[0]
            sf = web_source_file(slug)
            sf.parent.mkdir(parents=True, exist_ok=True)
            sf.write_text(md.strip(), encoding="utf-8")
            conn.execute("UPDATE sources SET source_path=?, status='source_ready', pdf_fetched_at=? WHERE id=?",
                         (str(sf.relative_to(ROOT)), now_iso(), url))
            store.set_paper_topic(conn, topic_id, p, 0)
            conn.commit()
            added += 1
            log.info(f"  OK [rel {it.get('relevance')}|{len(md) // 1024}KB] {p['title'][:50]}  ({domain})")
    finally:
        if chrome_ok and tb:
            tb.close_chrome()
        if lock_fp:
            lock_fp.close()

    conn.close()
    log.info(f"\n# web discover done: +{added} 篇入库(kind=web, status=source_ready, 不进总结)")
    run_log(topic_id, f"discover_web: +{added} web sources")


if __name__ == "__main__":
    main()
