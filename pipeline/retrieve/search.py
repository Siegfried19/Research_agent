"""混合召回:FTS5 关键词(对字) + 向量(对意思),用 RRF 融合成一个排名。

- FTS5 那路 = 从 ask.py 移来的 trigram 全文搜(标题/摘要/中文总结),管术语/缩写/精确短语。
- 向量那路 = index.knn,管概念/同义/症状(对字不对意思的解药)。
- RRF(Reciprocal Rank Fusion):两路各自排名,按 1/(K+rank) 相加 → 取长补短,无需调权重。
- 统一在 paper_id 空间融合(FTS 的 slug 经 papers 表映射到 paper_id)。

向量那路需 research-agent 环境(torch);FTS 那路纯 stdlib,可单独用。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import re
import sqlite3

from lib.db import open_db, ROOT
from lib.log import get_logger

FTS_PATH = ROOT / "db" / "fts.sqlite"
log = get_logger("search")

# 查询切分用的中文功能词(长词在前,先切长的) —— 与旧 ask.py 一致
CJK_STOP = ["为什么", "怎么样", "怎样", "怎么", "如何", "什么", "哪些", "哪个", "是否",
            "可以", "能否", "应该", "我们", "有没有", "关于",
            "的", "了", "吗", "呢", "在", "和", "与", "或", "及", "用", "做", "是"]
EN_STOP = set("the a an and or of for in on to with how what why when is are does do "
              "can could should about any using use".split())


# ---------------- FTS5 那路(对字) ----------------
def ensure_fts(force=False):
    """(增量)建 db/fts.sqlite:trigram 索引 标题+摘要+最新中文总结,按 slug 键。"""
    main = open_db()
    fts = sqlite3.connect(str(FTS_PATH))
    fts.executescript(
        "CREATE VIRTUAL TABLE IF NOT EXISTS fts_sum USING fts5(slug, body, tokenize='trigram');"
        "CREATE TABLE IF NOT EXISTS meta (slug TEXT PRIMARY KEY, sum_mtime REAL);")
    latest = {}
    for r in main.execute("SELECT paper_id, path, version FROM summary_versions ORDER BY paper_id, version"):
        latest[r["paper_id"]] = r["path"]
    seen = {r[0]: (r[1] or 0) for r in fts.execute("SELECT slug, sum_mtime FROM meta")}
    n = 0
    for p in main.execute("SELECT id, slug, title, abstract FROM papers WHERE slug IS NOT NULL"):
        spath = ROOT / latest[p["id"]] if p["id"] in latest else None
        sm = spath.stat().st_mtime if spath and spath.exists() else 0
        if not force and seen.get(p["slug"]) == sm:
            continue
        body = p["title"] or ""
        if p["abstract"]:
            body += "\n" + p["abstract"]
        if sm:
            body += "\n" + spath.read_text(encoding="utf-8", errors="replace")
        fts.execute("DELETE FROM fts_sum WHERE slug=?", (p["slug"],))
        fts.execute("INSERT INTO fts_sum VALUES (?,?)", (p["slug"], body))
        fts.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (p["slug"], sm))
        n += 1
    fts.commit()
    main.close()
    if n:
        log.info(f"fts index: {n} 篇(重)索引 -> {FTS_PATH.relative_to(ROOT)}")
    return fts


def parse_query(q):
    """-> (英文词, 中文≥3字段做trigram短语, 中文2字词)"""
    en = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", q) if w.lower() not in EN_STOP]
    runs = re.findall(r"[一-鿿]+", q)
    segs = []
    for run in runs:
        for sw in CJK_STOP:
            run = run.replace(sw, " ")
        segs += [s for s in run.split() if len(s) >= 2]
    cjk3 = []
    for s in segs:
        if len(s) <= 4:
            if len(s) >= 3:
                cjk3.append(s)
        else:
            cjk3 += [s[i:i + 3] for i in range(len(s) - 2)]
    return en, list(dict.fromkeys(cjk3)), [s for s in segs if len(s) == 2]


def fts_rank(fts, q):
    """FTS 那路:返回 [slug] 按相关性降序(bm25 + 2字词 instr 兜底)。"""
    en, cjk3, cjk2 = parse_query(q)
    scores = {}
    m = " OR ".join(f'"{t}"' for t in dict.fromkeys(en + cjk3))
    if m:
        for slug, bm in fts.execute(
                "SELECT slug, bm25(fts_sum) FROM fts_sum WHERE fts_sum MATCH ?", (m,)):
            scores[slug] = scores.get(slug, 0) + (-bm)
    for t in cjk2:  # trigram 索引不到 2 字词 → 全扫兜底(FTS5 上 LIKE 静默返0,必须 instr)
        for (slug,) in fts.execute("SELECT slug FROM fts_sum WHERE instr(body,?)>0", (t,)):
            scores[slug] = scores.get(slug, 0) + 1.0
    return [s for s, _ in sorted(scores.items(), key=lambda kv: -kv[1])]


# ---------------- 向量那路(对意思) ----------------
def vec_rank(query, k=50):
    """向量那路:返回 [paper_id] 按相似度降序。需 research-agent 环境。"""
    from lib import embed
    from retrieve import index
    db = index.connect()
    qv = embed.embed_query(query)
    return [pid for pid, _dist in index.knn(db, qv, k)]


# ---------------- RRF 融合 ----------------
def rrf_fuse(rankings, K=60):
    """多路排名 → RRF 合并。rankings=[[id,...], ...]。返回 [(id, score)] 降序。"""
    score = {}
    for ranking in rankings:
        for rank, _id in enumerate(ranking):
            score[_id] = score.get(_id, 0.0) + 1.0 / (K + rank)
    return sorted(score.items(), key=lambda kv: -kv[1])


def hybrid(query, topn=20, k=50, use_vec=True):
    """混合召回。返回 topn 个 paper 行(dict),按 RRF 融合分降序。"""
    main = open_db()
    slug2pid = {r["slug"]: r["id"] for r in main.execute("SELECT id, slug FROM papers WHERE slug IS NOT NULL")}

    fts = ensure_fts()
    fts_ids = [slug2pid[s] for s in fts_rank(fts, query) if s in slug2pid]
    rankings = [fts_ids]
    if use_vec:
        try:
            rankings.append(vec_rank(query, k))
        except Exception as e:
            log.info(f"向量那路不可用(回退纯FTS): {type(e).__name__}: {str(e)[:60]}")

    fused = rrf_fuse(rankings)[:topn]
    hits = []
    for pid, sc in fused:
        p = main.execute("SELECT * FROM papers WHERE id=?", (pid,)).fetchone()
        if p:
            hits.append({"paper": p, "score": sc})
    main.close()
    return hits
