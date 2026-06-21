"""Fetch web sources（拉正文 + 落盘）—— 论文线 fetch_oa 的 web 对应物。
读该主题 kind='web' 且 status IN('discovered','source_failed') 的来源,把正文抓成干净
markdown 落到 storage/sources/<slug>/source.md,入库 status='source_ready'。

抓取工具箱**摆给 agent,怎么抓/怎么看它自己定**(agent-first):静态页 WebFetch;
动态/X/登录墙用真 Chrome(复用 fetch_tierb 的生命周期:独占锁 + ensure,finally 收尾)。
设 WEB_NO_CHROME=1 强制纯静态(不起 Chrome)。

发现哪些 web 是 find 的活(find/discover_web.py);本脚本只管"拉下来落盘"。
run.py 的 fetch 阶段会在 fetch_oa 之后顺带跑本脚本(无 web 待抓则空转)。
Usage: python3 pipeline/fetch/fetch_web.py <topicId|all>
"""
import os
import sys
from urllib.parse import urlparse

# --- path shim: 让 `from lib...` 解析到 pipeline/lib,无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.claude import run_claude
from lib.db import open_db, ROOT, now_iso
from lib.log import get_logger, run_log
from lib.slug import file_id
from lib.store import web_source_file

log = get_logger("fetch_web")

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
        print("usage: fetch_web.py <topicId|all>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    conn = open_db()
    if topic_id == "all":
        rows = conn.execute(
            "SELECT * FROM sources WHERE kind='web' AND status IN ('discovered','source_failed')").fetchall()
    else:
        rows = conn.execute(
            """SELECT p.* FROM sources p JOIN source_topic pt ON pt.paper_id=p.id
                WHERE pt.topic_id=? AND p.kind='web' AND p.status IN ('discovered','source_failed')
                ORDER BY pt.rank""", (topic_id,)).fetchall()

    log.info(f"# web fetch: {len(rows)} 篇待抓正文")
    if not rows:
        conn.close()
        run_log(topic_id, "fetch_web: 0 待抓")
        return

    chrome_ok, alias, lock_fp, tb = start_chrome()
    ok = fail = 0
    try:
        for i, r in enumerate(rows):
            url = r["id"]
            base = r["slug"] or file_id(url)
            shot = ROOT / "storage" / "dl_tmp" / f"web_shot_{i}.png"
            shot.parent.mkdir(parents=True, exist_ok=True)
            sec = _chrome_section(url, alias, shot, chrome_ok)
            tools = ["WebFetch", "Bash", "Read"] if chrome_ok else ["WebFetch"]
            md = run_claude(FETCH_PROMPT.format(url=url, chrome_section=sec), timeout=600, tools=tools)
            if not md or md.strip() == "FAILED" or len(md.strip()) < 200:
                conn.execute("UPDATE sources SET status='source_failed', pdf_fetched_at=? WHERE id=?",
                             (now_iso(), url))
                conn.commit()
                fail += 1
                log.info(f"  FAIL(抓取失败/过短) {url}")
                continue
            sf = web_source_file(base)
            sf.parent.mkdir(parents=True, exist_ok=True)
            sf.write_text(md.strip(), encoding="utf-8")
            conn.execute("UPDATE sources SET source_path=?, status='source_ready', pdf_fetched_at=? WHERE id=?",
                         (str(sf.relative_to(ROOT)), now_iso(), url))
            conn.commit()
            ok += 1
            log.info(f"  OK [{len(md) // 1024}KB] {(r['title'] or '')[:50]}  ({urlparse(url).netloc})")
    finally:
        if chrome_ok and tb:
            tb.close_chrome()
        if lock_fp:
            lock_fp.close()

    conn.close()
    log.info(f"\n# web fetch done: {ok} 落盘 source_ready, {fail} 失败")
    run_log(topic_id, f"fetch_web: {ok} ok, {fail} failed")


if __name__ == "__main__":
    main()
