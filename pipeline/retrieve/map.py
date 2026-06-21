"""库地图(LIBRARY MAP)—— 知识库出口的"目录/索引"层。

来查的 agent **拥有调查循环**:它先跑这个脚本拿一张当前库地图(有什么、在哪、什么状态),
再自己决定读哪些总结 / 下钻哪些原件、得出结论。本脚本不问答、不检索、不调任何 LLM。

设计要点(见 claude-memory/modules-modification/retrieve/):
- 地图 = 对 DB + 主题状态档的**派生投影**(可重建),不是 DB 里的表;落 data-base/INDEX.md
  (gitignored,与 fts/vec 同类)。
- 纯 stdlib(sqlite3+json+datetime),**不走 envguard、不碰 conda/torch**——挂载点上裸
  python3、只读挂载都能跑。
- 标记说大白话 + 头部带图例,**agent 不用背我们的内部代码**;质量四档/核查六态各收成
  agent 真正会区别对待的少数几类。
- 收录"有料可读"的源(有总结**或**有原件文件);纯元数据不进。
- 两级分组 topic → facet;组内按年份降序(相关度是"对主题"的、不是"对 agent 题目"的,故不放)。

数据源(3 处,都 stdlib 可读):
- data-base/papers.sqlite : 标题/年/venue/质量档/kind/原件路径/id + 最新总结版本
- topics/*/verify_status.json : 核查态(经 lib.verify_status 解析)
- topics/*/selected.json : facet(find 子方向,不在 DB)

用法:  python3 pipeline/retrieve/map.py        # 打到 stdout + 写 data-base/INDEX.md
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

from lib.db import ROOT, DB_PATH
from lib.verify_status import load_verify_status, resolve_verify

INDEX_PATH = ROOT / "data-base" / "INDEX.md"

LEGEND = ("# 标记: 预印本=未同行评审 | 掠夺刊嫌疑=出处存疑 | 重大存疑=核查疑写错,建议核原文 | "
          "小瑕疵=核查见轻微问题,基本可信 | 未充分核查=未经/未充分交叉核验 | 〔网络源〕=博客/工具文,非论文")
GUIDE = "# 怎么调查(目录布局/读法/引用纪律): 项目根 instruction-for-other-agent.md"

NO_TOPIC = "（未归主题）"
NO_FACET = "（未分面）"


def _quality_mark(tier, kind):
    """质量档 → 大白话标记(只在异常时出)。web 源没有学术质量概念,统一标〔网络源〕。"""
    if kind == "web":
        return "〔网络源〕"
    return {"flag": "预印本(未评审)", "suspect": "掠夺刊嫌疑"}.get(tier or "")


def _verify_mark(state):
    """核查态 → 大白话标记(三档,对 agent 应对不同):major→重大存疑(核过、疑写错);
    minor→小瑕疵(核过、轻微问题,基本可信);stale/unverified/unverifiable→未充分核查
    (当前版没核/没核全,别全信、要紧下钻)。pass/无总结 不出。"""
    if state == "major":
        return "重大存疑"
    if state == "minor":
        return "小瑕疵"
    if state in ("stale", "unverified", "unverifiable"):
        return "未充分核查"
    return None


def _connect_ro():
    """只读连库(survive 只读挂载);失败回退普通连接。"""
    try:
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return sqlite3.connect(str(DB_PATH))


def gather():
    """读三处数据源 → (groups, n_papers, n_topics, titles)。
    groups: {topic_id: [entry,...]};entry = dict(facet,title,year,venue,quality,kind,
    verify,ver,sum_path,src_path,id)。只含"有料可读"的源。"""
    db = _connect_ro()
    db.row_factory = sqlite3.Row

    # 最新总结版本: paper_id -> (version, path)
    latest = {}
    for r in db.execute("SELECT paper_id, version, path FROM summary_versions"):
        pid, v = r["paper_id"], r["version"]
        if pid not in latest or v > latest[pid][0]:
            latest[pid] = (v, r["path"])

    # facet: (topic_id, paper_id) -> facet  (不在 DB,读主题状态档 selected.json)
    facet_map = {}
    for sp in (ROOT / "topics").glob("*/selected.json"):
        tid = sp.parent.name
        try:
            items = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("id") and it.get("facet"):
                    facet_map[(tid, it["id"])] = it["facet"]

    status_map = load_verify_status()

    # 源元数据 + "有料可读"过滤(总结文件或原件文件真实存在)
    material = {}
    for r in db.execute("SELECT id, title, year, venue, quality_tier, kind, source_path FROM sources"):
        pid = r["id"]
        ver, spath = latest.get(pid, (None, None))
        sum_exists = bool(spath and (ROOT / spath).exists())
        src_path = r["source_path"]
        src_exists = bool(src_path and (ROOT / src_path).exists())
        if not (sum_exists or src_exists):
            continue
        material[pid] = {
            "id": pid, "title": r["title"], "year": r["year"], "venue": r["venue"],
            "quality": r["quality_tier"], "kind": r["kind"],
            "verify": resolve_verify(status_map, pid, ver if sum_exists else None),
            "ver": ver if sum_exists else None,
            "sum_path": spath if sum_exists else None,
            "src_path": src_path if src_exists else None,
        }

    # 主题归属(一篇可属多主题,在每个主题下各出现一次)
    groups = defaultdict(list)
    in_topic = set()
    for r in db.execute("SELECT topic_id, paper_id FROM source_topic"):
        tid, pid = r["topic_id"], r["paper_id"]
        if pid in material:
            in_topic.add(pid)
            entry = dict(material[pid], facet=facet_map.get((tid, pid)))
            groups[tid].append(entry)
    for pid in material:
        if pid not in in_topic:
            groups[NO_TOPIC].append(dict(material[pid], facet=None))

    titles = {r["id"]: r["title"] for r in db.execute("SELECT id, title FROM topics")}
    db.close()
    n_topics = len([t for t in groups if t != NO_TOPIC])
    return groups, len(material), n_topics, titles


def _entry_lines(e):
    """一个 entry → 两行 markdown。第二行给**一次**家目录 + 里面的文件名(总结/原件同在
    storage/sources/<slug>/,不重复 slug),省体量。"""
    marks = [m for m in (_quality_mark(e["quality"], e["kind"]), _verify_mark(e["verify"])) if m]
    suffix = (" " + " · ".join(marks)) if marks else ""
    meta = ", ".join(x for x in [str(e["year"]) if e["year"] else None, e["venue"]] if x)
    head = f"- {e['title']}" + (f" ({meta})" if meta else "") + suffix
    ref = e["sum_path"] or e["src_path"]
    home = _os.path.dirname(ref) if ref else ""
    files = [_os.path.basename(e["sum_path"]) if e["sum_path"] else "(无总结)"]
    if e["src_path"]:
        files.append(_os.path.basename(e["src_path"]))  # paper.pdf / source.md
    return [head, f"      {home}/ : {' + '.join(files)} | id:{e['id']}"]


def _year_key(e):
    """年份降序、无年份垫底。"""
    return (e["year"] is None, -(e["year"] or 0), (e["title"] or "").lower())


def render():
    groups, n_papers, n_topics, titles = gather()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    out = [f"# 库地图 · 生成于 {ts} · 共 {n_papers} 篇 / {n_topics} 主题", LEGEND, GUIDE, ""]

    topic_ids = sorted((t for t in groups if t != NO_TOPIC))
    if NO_TOPIC in groups:
        topic_ids.append(NO_TOPIC)

    for tid in topic_ids:
        entries = groups[tid]
        if tid == NO_TOPIC:
            out.append(f"## {NO_TOPIC}")
        else:
            title = titles.get(tid)
            out.append(f"## {tid}" + (f" — {title}" if title else ""))

        facets = {e["facet"] for e in entries}
        if facets == {None}:
            for e in sorted(entries, key=_year_key):
                out += _entry_lines(e)
        else:
            ordered = sorted((f for f in facets if f), key=str)
            if None in facets:
                ordered.append(None)
            for f in ordered:
                out.append(f"### {f if f else NO_FACET}")
                for e in sorted((x for x in entries if x["facet"] == f), key=_year_key):
                    out += _entry_lines(e)
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main():
    text = render()
    sys.stdout.write(text)
    try:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(text, encoding="utf-8")
    except OSError as exc:  # 只读挂载等:stdout 已给到,落盘失败不致命
        sys.stderr.write(f"[map] 写 {INDEX_PATH} 失败(stdout 仍可用): {exc}\n")


if __name__ == "__main__":
    main()
