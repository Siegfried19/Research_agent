"""全读模式(方案④,2026-06-19 用户拍板的现规模默认出口)。

思路(白话):库小的时候不做检索预筛——python 把【库里所有"有总结"的论文清单】(标题+
⚠️标记+slug+总结路径+pdf路径,**正文不进 prompt,方案B**)塞给一个 Opus,给它 Read+Task:
它自己把这些总结都读一遍(篇数不多=召回地板、一篇不漏)、相关且要精确的再 Read PDF 一手、
要深读的多了可 Task 开子 agent 并行读(子 agent 只回证据、合并由主 Opus 单线程收口)。

为什么"清单+按需读"而不是"总结全文贴进 prompt":prompt 短(每次查询不重发几十万字)、不稀释
注意力;代价=召回靠模型读全(现在篇数少能读全→不漏,库大了会变只挑着读,那时再上检索筛)。

设计落点 → claude-memory/Prompt-structure-design/qa-layer-design.md §8/§9(金字塔);五方案速查 → §10。
契约(DOI/质量态/核查态回填、⚠️标记、哨兵)复用 answer.py(共享契约层),DOI 由程序回填=零幻觉。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import json
import re

from lib.db import open_db, ROOT
from lib.claude import run_claude
from lib.log import get_logger
from retrieve import answer

log = get_logger("readall")

PROMPT = """你是研究论文知识库的问答助手。来问的通常是另一个卡在自己项目里的 AI——它有你没有的\
项目上下文。下面是库里【带中文总结的论文清单】——只给了标题/标记/路径,总结正文和 PDF 没直接\
给你,你需要时用 Read 自己去开。

## 你的工具
- Read:打开任意一条 [n] 给的「总结」路径(中文结构化总结)或「pdf」路径(英文原文一手)。
- Task:当你要深读的篇数多到一个上下文读不过来时,可以开子 agent 并行读。每个子 agent 只读\
【你指定的一篇】→ 回【带出处的原文证据/数字】;别让它写小总结、别让它下结论(那会掉数字、\
张冠李戴)。合并、最终的 [n] 引用/哨兵/JSON 输出,全由你主 agent 单线程收口,绝不外包。
- 没有别的工具(不联网、不搜索)——论文已全列在下面,不需要"找"。

## 怎么做
1. 看清单,把【每一篇的总结都 Read 一遍】(篇数不多,别漏);拿不准相不相关也读一下。
2. 相关、且需要精确数字/方法/边界的,再 Read 它的 PDF 读一手。
3. 用读到的内容回答,每句末标来源 [n]。

## 纪律
4. 闭集引用:只引下面清单里列出的论文,【绝不】编造库外来源或 DOI。
5. 诚实:读完这些材料仍撑不起答案 → 明说"库里没有相关内容",【绝不用库外知识硬答】。
6. 总结是"地图"、有意略去了精确数字;要精确就以你 Read 的 PDF 为准。
7. 源标了 ⚠️ 低可信/预印本/核查存疑 的,引用时必须显式提醒该结论待核实。
8. 给对方蒸馏答案 + 出处指针(含 pdf 路径让它自己深钻),别把原文整段倒给它。

## 问题
{question}

## 论文清单(这些都有中文总结,需要哪篇自己 Read)
{catalog}

## 输出
先写中文答案(带 [n])。最后单独给一个 ```json 代码块(只这两个字段,DOI/路径由程序回填,你不用写):
```json
{{"answerable": true, "cited": [{{"n": 1, "slug": "..."}}]}}
```
答不了就 answerable=false、cited 留空、答案写"库里没有相关内容。"
"""


def load_papers(main, topic=None):
    """范围内"有总结"的论文行。默认全库(跨主题);--topic 限一个主题、按 rank 排。"""
    have_sum = "p.id IN (SELECT DISTINCT paper_id FROM summary_versions)"
    if topic:
        return main.execute(
            f"SELECT p.* FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id "
            f"WHERE pt.topic_id=? AND {have_sum} ORDER BY pt.rank", (topic,)).fetchall()
    return main.execute(
        f"SELECT p.* FROM papers p WHERE {have_sum} ORDER BY p.year DESC").fetchall()


def build_catalog(main, status_map, rows):
    """rows → (清单文本, index_map{n: paper行})。清单只放标题/⚠️标记/slug/两路径,正文不放。"""
    lines, index_map = [], {}
    for n, p in enumerate(rows, 1):
        ver, path = answer._latest_version(main, p["id"])
        vstatus = answer.resolve_verify(status_map, p["id"], ver)
        note = answer.TIER_NOTE.get(p["quality_tier"] or "", "") + answer.VERIFY_NOTE.get(vstatus or "", "")
        spath = str(ROOT / path) if path and (ROOT / path).exists() else "（总结缺失）"
        ppath = str(ROOT / p["pdf_path"]) if p["pdf_path"] else "（无PDF）"
        lines.append(f"[{n}] {p['title']} ({p['year']}, {p['venue'] or '?'}){note}\n"
                     f"    slug={p['slug']}  总结={spath}  pdf={ppath}")
        index_map[n] = p
    return "\n\n".join(lines), index_map


def _extract_json(out):
    """从模型输出抽末尾的 {answerable, cited}。先认 ```json 围栏,再平衡括号兜底;
    解析不出返回 None(调用方机械兜底,不瞎编)。"""
    for pat in (r"```json\s*(.*?)```", r"```\s*(\{.*?\})\s*```"):
        for blk in re.findall(pat, out, re.S):
            try:
                o = json.loads(blk.strip())
                if isinstance(o, dict) and "answerable" in o:
                    return o
            except Exception:  # noqa: BLE001
                pass
    for m in re.finditer(r"\{", out):  # 无围栏:逐个 { 做平衡扫描
        depth, start = 0, m.start()
        for i in range(start, len(out)):
            if out[i] == "{":
                depth += 1
            elif out[i] == "}":
                depth -= 1
                if depth == 0:
                    chunk = out[start:i + 1]
                    if "answerable" in chunk:
                        try:
                            o = json.loads(chunk)
                            if isinstance(o, dict) and "answerable" in o:
                                return o
                        except Exception:  # noqa: BLE001
                            pass
                    break
    return None


def _strip_json(out):
    """把 ```json...``` 围栏从答案正文里去掉(人看的 --answer 不该带那坨 JSON)。"""
    return re.sub(r"```json\s*.*?```", "", out, flags=re.S).strip()


def run(question, topic=None, limit=None):
    """全读模式回答。返回 {answerable, text, sources} —— 形状对齐 answer.build,
    ask.py 两条出口(readall/pipeline)同样消费。limit 当前不裁剪(全读本就要全看),留作签名兼容。"""
    main = open_db()
    status_map = answer.load_verify_status()
    rows = load_papers(main, topic)
    if not rows:
        main.close()
        scope = f"主题 {topic}" if topic else "库"
        log.info(f"全读模式:{scope}里没有带总结的论文 → 哨兵")
        return {"answerable": False, "text": answer.CANNOT, "sources": []}

    catalog, index_map = build_catalog(main, status_map, rows)
    log.info(f"全读模式:{len(rows)} 篇清单 → claude(Read+Task)")
    out = run_claude(PROMPT.format(question=question, catalog=catalog),
                     tools=["Read", "Task"], timeout=1800)

    parsed = _extract_json(out)
    text = _strip_json(out)
    if not parsed:
        log.info("全读模式:输出 JSON 解析失败 → 机械兜底 answerable=false(不瞎编)")
        main.close()
        return {"answerable": False, "text": text or "无法确定（输出解析失败）。", "sources": []}

    sources = []
    for c in (parsed.get("cited") or []):
        n = c.get("n") if isinstance(c, dict) else c
        slug = c.get("slug") if isinstance(c, dict) else None
        p = index_map.get(n)
        if p is None and slug:  # n 对不上,用 slug 兜底找回
            p = next((pp for pp in index_map.values() if pp["slug"] == slug), None)
        if p is None:
            log.info(f"全读模式:cited 项 n={n} slug={slug} 在清单里找不到,跳过")
            continue
        if slug and p["slug"] != slug:
            log.info(f"全读模式:cited n={n} slug 不一致(模型给 {slug}/实为 {p['slug']}),以 n 为准")
        sources.append({"n": n, **answer.make_source(main, status_map, p)})

    main.close()
    return {"answerable": bool(parsed.get("answerable")), "text": text, "sources": sources}
