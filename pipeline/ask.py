"""Ask the paper library a question — 出口①② 公共API(路径冻结,勿移)。

  python3 pipeline/ask.py "<问题>" [-n N] [--json] [--answer] [--reindex] [--no-rerank]

检索流水线(内脏在 pipeline/retrieve/):
  混合召回(FTS5 关键词 + 向量语义, RRF 融合) → claude -p RCS 精挑 → 带引用回答 / 会说不知道。
向量那路需 research-agent conda 环境(torch);**base 环境自动回退纯 FTS**(仍可用,只是少了语义召回)。

  默认       人看的命中列表(快,纯召回,不调 claude)
  --answer   claude -p 综合给带引用中文回答(撑不住就老实说"库里没有")
  --json     机器可读(给外部 agent):{answerable, answer, sources:[{doi,summary_path,pdf_path,quality_tier}]}
  --reindex  重建索引(fts + vec)
  --no-rerank  --answer/--json 时跳过 RCS 精挑(快,但不精排)
  --no-understand  跳过 claude 问题理解层,直接用机械分词(快,但治不了缩写/中文复合词)

默认对所有查询都先过 claude 问题理解层(展开缩写 + 中英双语词 + HyDE),根治机械分词的
P-A(2字母缩写被丢)/P-B(中文复合词被劈)。claude 失败自动回退机械分词,不阻断检索。
"""
# --- path shim: 让 `from lib...`/`from retrieve...` 解析到 pipeline/ ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from lib.envguard import ensure_env
ensure_env()  # 不在 research-agent 环境就自动切过去(向量检索要 torch;否则回退纯 FTS)

import argparse
import json

from lib.log import get_logger
from retrieve import search, understand

log = get_logger("ask")


def reindex(force=False):
    """保证 fts + vec 两个索引都最新(各自增量)。无 torch 环境下静默跳过 vec。"""
    search.ensure_fts(force=force)
    try:
        from retrieve import index
        index.build_index(force=force)
    except ImportError:
        log.info("向量索引跳过(当前环境无 sqlite_vec/torch;FTS 仍可用)")


def _show_hits(q, hits):
    from lib.db import open_db
    print(f"# 库内检索: {q}  ({len(hits)} 命中)\n")
    main = open_db()
    for i, h in enumerate(hits, 1):
        p = h["paper"]
        tps = main.execute("SELECT topic_id, relevance FROM paper_topic WHERE paper_id=?",
                           (p["id"],)).fetchall()
        tline = ", ".join(f"{t['topic_id']}({t['relevance']:.0f})" for t in tps)
        tier = {"suspect": " ⚠️低可信", "flag": " (预印本)"}.get(p["quality_tier"] or "", "")
        print(f"{i}. [{h['score']:.3f}] {p['title']} ({p['year']}, {p['venue'] or '?'}){tier}")
        if tline:
            print(f"   主题: {tline}")
        print(f"   总结: store/summaries/{p['slug']}/  PDF: {p['pdf_path'] or '-'}\n")
    main.close()


def _show_answer(q, res):
    print(f"# 回答: {q}\n")
    print(res["text"])
    print("\n## 来源")
    for s in res["sources"]:
        tier = f" [{s['quality_tier']}]" if s["quality_tier"] else ""
        print(f"  [{s['n']}] {s['title']} ({s['year']}){tier}")
        if s["summary_path"]:
            print(f"      总结: {s['summary_path']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default="")
    ap.add_argument("-n", type=int, default=8)
    ap.add_argument("--json", action="store_true", help="机器可读输出(给外部 agent)")
    ap.add_argument("--answer", action="store_true", help="claude -p 综合给带引用回答")
    ap.add_argument("--reindex", action="store_true", help="重建 fts + vec 索引")
    ap.add_argument("--no-rerank", action="store_true", help="跳过 RCS 精挑(快)")
    ap.add_argument("--no-understand", action="store_true", help="跳过 claude 问题理解层(快,但不治缩写/中文复合词)")
    a = ap.parse_args()

    reindex(force=a.reindex)
    if not a.question:
        if not a.reindex:
            ap.print_help()
        return

    understanding = None if a.no_understand else understand.understand_query(a.question)
    deep = a.answer or a.json
    hits = search.hybrid(a.question, topn=max(a.n, 20) if deep else a.n, understanding=understanding)
    if not hits:
        if a.json:
            print(json.dumps({"query": a.question, "understanding": understanding,
                              "answerable": False, "answer": "", "sources": []},
                             ensure_ascii=False))
        else:
            print("库里没有命中。换关键词试试。")
        return

    if deep:
        from retrieve import answer
        ranked = hits[:a.n]
        if not a.no_rerank:
            from retrieve import rerank
            ranked = rerank.rcs_rerank(a.question, hits, keep=a.n)
        res = answer.build(a.question, ranked)
        if a.json:
            print(json.dumps({"query": a.question, "understanding": understanding,
                              "answerable": res["answerable"],
                              "answer": res["text"], "sources": res["sources"]},
                             ensure_ascii=False, indent=1))
        else:
            _show_answer(a.question, res)
    else:
        _show_hits(a.question, hits)


if __name__ == "__main__":
    main()
