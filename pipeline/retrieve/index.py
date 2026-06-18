"""坐标索引:把每篇论文(标题+摘要+最新中文总结)量成向量,存进 db/vec.sqlite。

- 可重建副本,**不碰**生产 db/papers.sqlite。
- 增量式:body 内容哈希没变就跳过,不重嵌(对齐 ask.py 的 fts 增量思路)。
- 没总结的论文也嵌(用 标题+摘要),所以"找相似/揪重复"对全库 221 篇都生效,不只已总结的。
- 需在 research-agent conda 环境跑(依赖 torch/sentence-transformers/sqlite-vec)。

CLI: python3 pipeline/retrieve/index.py [--force]
"""
# --- path shim: 让 `from lib...` 解析到 pipeline/lib ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import hashlib
import sqlite3
import sqlite_vec
from sqlite_vec import serialize_float32

from lib.db import open_db, ROOT
from lib.log import get_logger
from lib import embed

VEC_PATH = ROOT / "db" / "vec.sqlite"
DIM = 1024
log = get_logger("vec_index")


def connect():
    """打开 vec.sqlite(载入 sqlite-vec 扩展),建表(若无)。"""
    db = sqlite3.connect(str(VEC_PATH))
    db.row_factory = sqlite3.Row
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_papers USING vec0("
               f"paper_id TEXT PRIMARY KEY, embedding float[{DIM}] distance_metric=cosine)")
    db.execute("CREATE TABLE IF NOT EXISTS meta (paper_id TEXT PRIMARY KEY, body_hash TEXT)")
    return db


def paper_body(p, latest):
    """嵌入用文本:标题 + 摘要 + 最新总结(有就加)。"""
    parts = [p["title"] or ""]
    if p["abstract"]:
        parts.append(p["abstract"])
    sp = latest.get(p["id"])
    if sp and (ROOT / sp).exists():
        parts.append((ROOT / sp).read_text(encoding="utf-8", errors="replace"))
    return "\n".join(x for x in parts if x).strip()


def build_index(force=False):
    """(增量)重建坐标索引。返回打开的 vec.sqlite 连接。"""
    main = open_db()
    latest = {}
    for r in main.execute("SELECT paper_id, path, version FROM summary_versions ORDER BY paper_id, version"):
        latest[r["paper_id"]] = r["path"]            # 按 version 升序,后写覆盖=最高版
    db = connect()
    seen = {r["paper_id"]: r["body_hash"] for r in db.execute("SELECT paper_id, body_hash FROM meta")}

    todo = []
    for p in main.execute("SELECT id, slug, title, abstract FROM papers WHERE slug IS NOT NULL"):
        body = paper_body(p, latest)
        if not body:
            continue
        h = hashlib.md5(body.encode("utf-8")).hexdigest()
        if not force and seen.get(p["id"]) == h:
            continue
        todo.append((p["id"], body, h))
    main.close()

    if not todo:
        log.info("vec index: 无变化,跳过")
        return db

    vecs = embed.embed_documents([b for _, b, _ in todo])
    for (pid, _, h), v in zip(todo, vecs):
        db.execute("DELETE FROM vec_papers WHERE paper_id = ?", (pid,))
        db.execute("INSERT INTO vec_papers(paper_id, embedding) VALUES (?, ?)",
                   (pid, serialize_float32(v.tolist())))
        db.execute("INSERT OR REPLACE INTO meta(paper_id, body_hash) VALUES (?, ?)", (pid, h))
    db.commit()
    log.info(f"vec index: {len(todo)} 篇(重)嵌入 -> {VEC_PATH.relative_to(ROOT)}")
    return db


def knn(db, qvec, k=30):
    """查 k 近邻。返回 [(paper_id, distance)],distance=cosine距离(越小越像)。"""
    rows = db.execute(
        "SELECT paper_id, distance FROM vec_papers WHERE embedding MATCH ? AND k = ? ORDER BY distance",
        (serialize_float32(list(qvec)), k)).fetchall()
    return [(r["paper_id"], r["distance"]) for r in rows]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="全量重嵌(忽略哈希)")
    build_index(force=ap.parse_args().force)
