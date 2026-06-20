"""检索 A/B 验收(确定性,零额外 LLM):给一组 gold 问题(已知该命中哪些论文),
算 Recall@k / MRR,对比 纯FTS vs 混合(FTS+向量) —— 证明语义召回有没有真把准度提上去。

gold 文件 JSON 每条:{"q": "<问题>", "gold_titles": ["<标题关键词>", ...]} 或 {"q":..,"gold":["<doi>",..]}。
标题关键词按子串解析到 papers.id;hand-label 时写标题片段最省事。

  python3 pipeline/tools/eval_retrieval.py [store/eval_gold.json] [-k 10]

⚠️ 这是 harness + 种子。真正的 30–50 条 gold 该由用户按真实使用场景手标,且最好在"总结重做定稿"后再跑。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import json

from lib.db import open_db, ROOT
from retrieve import search


def resolve_gold(main, item):
    """把 gold_titles(标题子串) / gold(doi) 解析成 paper_id 集合。"""
    ids = set(item.get("gold", []))
    for kw in item.get("gold_titles", []):
        for r in main.execute("SELECT id FROM papers WHERE title LIKE ?", (f"%{kw}%",)):
            ids.add(r["id"])
    return ids


def metrics(ranked_ids, gold, k):
    topk = set(ranked_ids[:k])
    recall = 1.0 if (topk & gold) else 0.0
    rr = next((1.0 / i for i, pid in enumerate(ranked_ids, 1) if pid in gold), 0.0)
    return recall, rr


def run(gold_path, k):
    main = open_db()
    gold = json.loads((ROOT / gold_path).read_text(encoding="utf-8"))
    for item in gold:
        item["_gold"] = resolve_gold(main, item)
    main.close()

    print(f"gold 集 {len(gold)} 条, k={k}\n")
    print(f"{'配置':12} {'Recall@'+str(k):>10} {'MRR':>8}")
    print("-" * 34)
    for label, use_vec in [("纯 FTS", False), ("混合(+向量)", True)]:
        R = M = 0.0
        for item in gold:
            hits = search.hybrid(item["q"], topn=max(k, 50), use_vec=use_vec)
            ranked = [h["paper"]["id"] for h in hits]
            r, rr = metrics(ranked, item["_gold"], k)
            R += r
            M += rr
        n = len(gold)
        print(f"{label:12} {R/n:>10.2f} {M/n:>8.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("gold", nargs="?", default="storage/eval_gold.json")
    ap.add_argument("-k", type=int, default=10)
    run(ap.parse_args().gold, ap.parse_args().k)
