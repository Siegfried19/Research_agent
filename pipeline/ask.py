"""Ask the paper library a question — RAG stage ① (FTS5, zero deps).

  python3 pipeline/ask.py "<问题或关键词>" [-n N] [--json] [--answer] [--reindex]

主要用户是**别的项目里的 agent**(做任务卡住时来查),所以:
  --json  输出机器可读结果(绝对路径),拿到 summary_path/text_path 自己 Read 深读。
  人类/agent 通用工作流: 先检索 → 读最相关几篇的总结 → 需要细节再读全文。
可从任意 cwd 以绝对路径调用: python3 ~/Projects/Research_agent/pipeline/ask.py "..."

Index (db/fts.sqlite, disposable & rebuildable, NOT the production DB):
  fts_sum  trigram tokenizer — title + abstract + latest Chinese summary
  fts_text porter tokenizer  — English full text (store/text/*.txt)
Incremental: re-indexes a paper only when its summary/text file mtime changed.

Retrieval honours papers.quality_tier (标记进库,出口必须认标记):
  suspect -> score halved + ⚠️低可信 label; flag -> 预印本(未同行评审) note.

--answer feeds the top hits' summaries to headless claude -p and prints a cited
Chinese answer (says so explicitly when the library doesn't cover the question).
关键词式提问效果最好;整句也行(中文按停用词切段,英文取词)。
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

from lib.db import open_db, ROOT
from lib.log import get_logger

FTS_PATH = ROOT / "db" / "fts.sqlite"
log = get_logger("ask")

# 查询切分用的中文功能词(长词在前,先切长的)
CJK_STOP = ["为什么", "怎么样", "怎样", "怎么", "如何", "什么", "哪些", "哪个", "是否",
            "可以", "能否", "应该", "我们", "有没有", "关于",
            "的", "了", "吗", "呢", "在", "和", "与", "或", "及", "用", "做", "是"]
EN_STOP = set("the a an and or of for in on to with how what why when is are does do "
              "can could should about any using use".split())


def ensure_index(force=False):
    """(Re)build db/fts.sqlite incrementally from papers + summaries + full text."""
    main = open_db()
    fts = sqlite3.connect(str(FTS_PATH))
    fts.executescript(
        "CREATE VIRTUAL TABLE IF NOT EXISTS fts_sum  USING fts5(slug, body, tokenize='trigram');"
        "CREATE VIRTUAL TABLE IF NOT EXISTS fts_text USING fts5(slug, body, tokenize='porter unicode61');"
        "CREATE TABLE IF NOT EXISTS meta (slug TEXT PRIMARY KEY, sum_mtime REAL, text_mtime REAL);")
    latest = {r["paper_id"]: r["path"] for r in main.execute(
        "SELECT paper_id, path, MAX(version) FROM summary_versions GROUP BY paper_id")}
    seen = {r[0]: (r[1] or 0, r[2] or 0) for r in fts.execute("SELECT slug, sum_mtime, text_mtime FROM meta")}
    n = 0
    for p in main.execute("SELECT id, slug, title, abstract, text_path FROM papers WHERE slug IS NOT NULL"):
        spath = ROOT / latest[p["id"]] if p["id"] in latest else None
        tpath = ROOT / p["text_path"] if p["text_path"] else None
        sm = spath.stat().st_mtime if spath and spath.exists() else 0
        tm = tpath.stat().st_mtime if tpath and tpath.exists() else 0
        if not force and seen.get(p["slug"]) == (sm, tm):
            continue
        body = p["title"] or ""
        if p["abstract"]:
            body += "\n" + p["abstract"]
        if sm:
            body += "\n" + spath.read_text(encoding="utf-8", errors="replace")
        fts.execute("DELETE FROM fts_sum WHERE slug=?", (p["slug"],))
        fts.execute("INSERT INTO fts_sum VALUES (?,?)", (p["slug"], body))
        fts.execute("DELETE FROM fts_text WHERE slug=?", (p["slug"],))
        if tm:
            fts.execute("INSERT INTO fts_text VALUES (?,?)",
                        (p["slug"], tpath.read_text(encoding="utf-8", errors="replace")))
        fts.execute("INSERT OR REPLACE INTO meta VALUES (?,?,?)", (p["slug"], sm, tm))
        n += 1
    fts.commit()
    main.close()
    if n:
        log.info(f"index: {n} papers (re)indexed -> {FTS_PATH.relative_to(ROOT)}")
    return fts


def parse_query(q):
    """-> (english terms, CJK segs >=3 chars, CJK segs ==2 chars)"""
    en = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", q) if w.lower() not in EN_STOP]
    runs = re.findall(r"[一-鿿]+", q)
    segs = []
    for run in runs:
        for sw in CJK_STOP:
            run = run.replace(sw, " ")
        segs += [s for s in run.split() if len(s) >= 2]
    cjk3 = []
    for s in segs:
        if len(s) <= 4:           # 短段整段做精确短语
            if len(s) >= 3:
                cjk3.append(s)
        else:                     # 长段拆滑窗 trigram(OR 召回,bm25 按命中数排序)
            cjk3 += [s[i:i + 3] for i in range(len(s) - 2)]
    return en, list(dict.fromkeys(cjk3)), [s for s in segs if len(s) == 2]


def search(fts, q, topn):
    en, cjk3, cjk2 = parse_query(q)
    scores, snips = {}, {}

    def add(slug, sc, snip=None):
        scores[slug] = scores.get(slug, 0) + sc
        if snip and slug not in snips:
            snips[slug] = snip

    m_sum = " OR ".join(f'"{t}"' for t in dict.fromkeys(en + cjk3))
    if m_sum:
        for slug, bm, snip in fts.execute(
                "SELECT slug, bm25(fts_sum), snippet(fts_sum,1,'【','】','…',16) "
                "FROM fts_sum WHERE fts_sum MATCH ?", (m_sum,)):
            add(slug, -bm * 2.0, snip)  # 总结层权重 x2
    m_txt = " OR ".join(f'"{t}"' for t in dict.fromkeys(en))
    if m_txt:
        for slug, bm, snip in fts.execute(
                "SELECT slug, bm25(fts_text), snippet(fts_text,1,'【','】','…',16) "
                "FROM fts_text WHERE fts_text MATCH ?", (m_txt,)):
            add(slug, -bm, snip)
    for t in cjk2:  # trigram 索引不到 2 字词 -> 总结层 instr 全扫兜底(语料小,扫得动;
        # 注意 FTS5 虚拟表上 LIKE 静默返回 0 行,必须用 instr)
        for (slug,) in fts.execute("SELECT slug FROM fts_sum WHERE instr(body,?)>0", (t,)):
            add(slug, 1.0)
    if not scores:
        return []

    main = open_db()
    hits = []
    for slug, sc in scores.items():
        p = main.execute("SELECT * FROM papers WHERE slug=?", (slug,)).fetchone()
        if not p:
            continue
        tier = p["quality_tier"]
        if tier == "suspect":
            sc *= 0.5  # 出口认标记:可疑来源降权 + 显式标注
        topics = main.execute("SELECT topic_id, relevance FROM paper_topic WHERE paper_id=?",
                              (p["id"],)).fetchall()
        hits.append({"slug": slug, "score": sc, "p": p, "topics": topics,
                     "snip": snips.get(slug, "")})
    main.close()
    hits.sort(key=lambda h: -h["score"])
    return hits[:topn]


def as_json(hits, q):
    import json as _json
    out = []
    for h in hits:
        p = h["p"]
        sdir = ROOT / "store" / "summaries" / h["slug"]
        vs = sorted(sdir.glob("v*.md"))
        out.append({
            "title": p["title"], "year": p["year"], "venue": p["venue"], "doi": p["doi"],
            "score": round(h["score"], 2),
            "quality_tier": p["quality_tier"],  # suspect=可疑来源慎引, flag=预印本未评审
            "topics": [{"id": t["topic_id"], "relevance": t["relevance"]} for t in h["topics"]],
            "snippet": h["snip"][:300],
            "summary_path": str(vs[-1]) if vs else None,   # 中文结构化总结(先读这个)
            "text_path": str(ROOT / p["text_path"]) if p["text_path"] else None,  # 英文全文
        })
    print(_json.dumps({"query": q, "hits": out}, ensure_ascii=False, indent=1))


def tier_label(p):
    return {"suspect": " ⚠️低可信来源", "flag": " (预印本,未同行评审)",
            "trusted": ""}.get(p["quality_tier"] or "", "")


def show(hits, q):
    print(f"# 库内检索: {q}  ({len(hits)} 命中)\n")
    for i, h in enumerate(hits, 1):
        p = h["p"]
        tline = ", ".join(f"{t['topic_id']}(rel {t['relevance']:.0f})" for t in h["topics"])
        print(f"{i}. [{h['score']:.1f}] {p['title']} ({p['year']}, {p['venue'] or '?'})"
              f"{tier_label(p)}")
        print(f"   主题: {tline}")
        if h["snip"]:
            print(f"   摘段: {h['snip'][:200]}")
        print(f"   总结: store/summaries/{h['slug']}/  全文: {p['text_path'] or '-'}\n")


def answer(hits, q):
    from lib.claude import run_claude
    blocks = []
    for i, h in enumerate(hits[:5], 1):
        sdir = ROOT / "store" / "summaries" / h["slug"]
        vs = sorted(sdir.glob("v*.md"))
        body = vs[-1].read_text(encoding="utf-8", errors="replace")[:5000] if vs else (h["p"]["abstract"] or "")
        blocks.append(f"[{i}] {h['p']['title']} ({h['p']['year']}, {h['p']['venue'] or '?'})"
                      f"{tier_label(h['p'])}\n{body}")
    prompt = (f"你是论文库问答助手。只基于下面提供的论文总结回答问题,引用时标 [编号]。\n"
              f"带 ⚠️低可信来源 标记的材料,引用时必须显式说明来源可疑。\n"
              f"材料覆盖不了的部分,直说\"库里没有\",不要编。用中文,简洁。\n\n"
              f"## 问题\n{q}\n\n## 材料\n" + "\n\n---\n\n".join(blocks))
    print("\n# 综合回答 (claude -p, 基于前 5 命中)\n")
    print(run_claude(prompt, timeout=300))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default="")
    ap.add_argument("-n", type=int, default=8)
    ap.add_argument("--json", action="store_true", help="机器可读输出(绝对路径),给 agent 用")
    ap.add_argument("--answer", action="store_true", help="claude -p 综合前5命中给出带引用的回答")
    ap.add_argument("--reindex", action="store_true", help="强制全量重建索引")
    a = ap.parse_args()
    if not a.question and not a.reindex:
        ap.print_help()
        sys.exit(1)
    fts = ensure_index(force=a.reindex)
    if not a.question:
        return
    hits = search(fts, a.question, a.n)
    if not hits:
        if a.json:
            print('{"query": %s, "hits": []}' % __import__("json").dumps(a.question, ensure_ascii=False))
        else:
            print("库里没有命中。换关键词试试(英文术语对全文层更有效)。")
        return
    if a.json:
        as_json(hits, a.question)
    else:
        show(hits, a.question)
    if a.answer:
        answer(hits, a.question)


if __name__ == "__main__":
    main()
