"""找相似 / 揪重复(旁路工具,手动跑)。直接读 data-base/vec.sqlite 里的坐标做 numpy 余弦,**不调 GPU**。

  python3 pipeline/tools/similar.py dup [--threshold 0.93]      # 揪全库疑似重复对
  python3 pipeline/tools/similar.py like "<doi或标题关键词>" [-k 5]  # 找跟某篇最像的

需 research-agent 环境(sqlite_vec 读 vec0 表)。坐标已归一化 → 点积=余弦。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import numpy as np

from lib.db import open_db
from retrieve import index


def load_matrix():
    db = index.connect()
    rows = db.execute("SELECT paper_id, embedding FROM vec_papers").fetchall()
    ids = [r["paper_id"] for r in rows]
    M = np.array([np.frombuffer(r["embedding"], dtype="<f4") for r in rows]) if rows else np.zeros((0, 1))
    return ids, M


def _titles(ids):
    main = open_db()
    t = {r["id"]: r["title"] for r in main.execute("SELECT id, title FROM sources")}
    main.close()
    return [t.get(i) or i for i in ids]


def cmd_dup(threshold):
    ids, M = load_matrix()
    ts = _titles(ids)
    S = M @ M.T
    pairs = [(float(S[a, b]), a, b) for a in range(len(ids)) for b in range(a + 1, len(ids))
             if S[a, b] >= threshold]
    pairs.sort(reverse=True)
    print(f"全库 {len(ids)} 篇,相似度 >= {threshold} 的对: {len(pairs)}")
    for s, a, b in pairs:
        print(f"  {s:.3f}  {ts[a][:48]}  ⟷  {ts[b][:48]}")
        print(f"         {ids[a]}  |  {ids[b]}")


def cmd_like(query, k):
    ids, M = load_matrix()
    ts = _titles(ids)
    idx = next((i for i, (pid, t) in enumerate(zip(ids, ts))
                if query.lower() == pid.lower() or query.lower() in (t or "").lower()), None)
    if idx is None:
        print("没找到匹配论文(按 doi 全等 或 标题含关键词)。")
        return
    sims = M @ M[idx]
    order = np.argsort(-sims)
    print(f"跟《{ts[idx][:55]}》最像的 {k} 篇:")
    for j in order[1:k + 1]:
        print(f"  {sims[j]:.3f}  {ts[j][:55]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("dup")
    d.add_argument("--threshold", type=float, default=0.93)
    lk = sub.add_parser("like")
    lk.add_argument("query")
    lk.add_argument("-k", type=int, default=5)
    a = ap.parse_args()
    if a.cmd == "dup":
        cmd_dup(a.threshold)
    elif a.cmd == "like":
        cmd_like(a.query, a.k)
    else:
        ap.print_help()
