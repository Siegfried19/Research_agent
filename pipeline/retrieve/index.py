"""坐标索引:把每篇论文(标题+摘要+最新中文总结)量成向量,存进 data-base/vec.sqlite。

- 可重建副本,**不碰**生产 data-base/papers.sqlite。
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

VEC_PATH = ROOT / "data-base" / "vec.sqlite"
DIM = 1024
log = get_logger("vec_index")


def connect():
    """打开 vec.sqlite(载入 sqlite-vec 扩展),建表(若无)。"""
    db = sqlite3.connect(str(VEC_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")  # C:两个查询并发写索引时别直接报 locked
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_papers USING vec0("
               f"paper_id TEXT PRIMARY KEY, embedding float[{DIM}] distance_metric=cosine)")
    db.execute("CREATE TABLE IF NOT EXISTS meta (paper_id TEXT PRIMARY KEY, cheap_key TEXT, body_hash TEXT)")
    cols = [r[1] for r in db.execute("PRAGMA table_info(meta)")]
    if "cheap_key" not in cols:  # 旧 schema(只有 body_hash)→重建 meta,强制全量一次(vec.sqlite 可重建)
        db.executescript("DROP TABLE meta; "
                         "CREATE TABLE meta (paper_id TEXT PRIMARY KEY, cheap_key TEXT, body_hash TEXT)")
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
    """(增量)重建坐标索引。返回打开的 vec.sqlite 连接。
    两段钥匙:便宜钥匙(stale_key)没变→跳过不读文件(快);变了→读全文算 body_hash 精确确认,
    内容真变才重嵌(贵),只是 mtime 被碰过→只更钥匙不重嵌。坐标永远与内容一致(零问答风险)。"""
    from retrieve.freshness import latest_summary_map, stale_key
    main = open_db()
    latest = latest_summary_map(main)
    db = connect()
    seen = {r["paper_id"]: (r["cheap_key"], r["body_hash"])
            for r in db.execute("SELECT paper_id, cheap_key, body_hash FROM meta")}

    todo = []       # (pid, body, body_hash, cheap_key) —— 内容真变,要重嵌
    keyonly = []    # (pid, cheap_key) —— 只 mtime 变内容没变,只更钥匙不重嵌
    qualifying = set()
    for p in main.execute("SELECT id, slug, title, abstract FROM sources WHERE slug IS NOT NULL"):
        qualifying.add(p["id"])
        path = latest.get(p["id"])
        spath = ROOT / path if path else None
        mtime = spath.stat().st_mtime if spath and spath.exists() else 0
        ck = stale_key(p["title"], p["abstract"], path, mtime)
        prev = seen.get(p["id"])
        if not force and prev and prev[0] == ck:
            continue                                  # 便宜钥匙没变 → 跳过,不读文件
        body = paper_body(p, latest)                  # 钥匙变了才读全文
        if not body:
            continue
        h = hashlib.md5(body.encode("utf-8")).hexdigest()
        if not force and prev and prev[1] == h:
            keyonly.append((p["id"], ck))             # 内容没变(mtime被碰)→ 只更钥匙
            continue
        todo.append((p["id"], body, h, ck))
    main.close()

    for pid, ck in keyonly:
        db.execute("UPDATE meta SET cheap_key=? WHERE paper_id=?", (ck, pid))
    orphans = [pid for pid in seen if pid not in qualifying]  # D:回收孤儿
    for pid in orphans:
        db.execute("DELETE FROM vec_papers WHERE paper_id=?", (pid,))
        db.execute("DELETE FROM meta WHERE paper_id=?", (pid,))

    if not todo:
        if keyonly or orphans:
            db.commit()
        log.info(f"vec index: 无需重嵌({len(keyonly)} 更钥匙, {len(orphans)} 孤儿回收)")
        return db

    vecs = embed.embed_documents([b for _, b, _, _ in todo])
    for (pid, _, h, ck), v in zip(todo, vecs):
        db.execute("DELETE FROM vec_papers WHERE paper_id = ?", (pid,))
        db.execute("INSERT INTO vec_papers(paper_id, embedding) VALUES (?, ?)",
                   (pid, serialize_float32(v.tolist())))
        db.execute("INSERT OR REPLACE INTO meta(paper_id, cheap_key, body_hash) VALUES (?, ?, ?)",
                   (pid, ck, h))
    db.commit()
    log.info(f"vec index: {len(todo)} 篇(重)嵌入, {len(keyonly)} 更钥匙, {len(orphans)} 孤儿回收 "
             f"-> {VEC_PATH.relative_to(ROOT)}")
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
