"""Ask the paper library a question.

⚠️ 降级说明(2026-06-21):知识库出口已重构为「**消费者拥有调查循环**」——来查的 agent
   先跑 `pipeline/retrieve/map.py` 拿库地图,自己决定读哪些总结/原件、自己得结论(库经
   SSH 挂载到主力机,全是本地文件读,不需要远程 API)。**`map.py` 是现在的主入口。**
   本文件(问答引擎:理解→召回→精排→生成答案)**降级为大库备用工具**——库大到 agent
   一个上下文读不完地图/总结时才用,留盘不删,不再是默认路径。详见
   claude-memory/modules-modification/retrieve/STATE.md。

—— 出口①② 公共API(路径冻结,勿移)。

  python3 pipeline/ask.py "<问题>" [-n N] [--json] [--answer] [--mode M] [--topic T] [--reindex] [--no-rerank]

**两种回答模式(--answer/--json 时,2026-06-19)**:
  --mode readall (默认,库小)  全读:python 把【全部带总结的论文清单】塞给一个 Opus(给 Read+Task),
                             它自己把总结读全(召回地板)、相关的再 Read PDF、多了可开子 agent 并行读。
                             不检索、不碰索引。内脏 retrieve/readall.py。设计见 claude-memory/Prompt-structure-design/qa-layer-design.md §8-§10。
  --mode pipeline (大库)      检索管道(方案A):混合召回(FTS5+向量,RRF) → claude -p RCS 精挑 → 带引用回答。
                             向量那路需 research-agent conda 环境(torch);base 环境自动回退纯 FTS。
  --topic <id>               限定只在某主题范围内问(默认全库跨主题)。

  默认(无--answer/--json)  人看的命中列表(快,纯召回,走混合召回,不调 claude)
  --answer   带引用中文回答(撑不住就老实说"库里没有")
  --json     机器可读(给外部 agent):{answerable, answer, sources:[{doi,quality_tier,verify_status,summary_path,source_path}]}
  --reindex  重建索引(fts + vec;全读模式用不到,pipeline/命中列表才用)
  --no-rerank  pipeline 模式跳过 RCS 精挑(快,但不精排)
  --no-understand  [debug专用] 跳过 claude 问题理解层走老机械分词;正常跑别用

默认对所有查询都先过 claude 问题理解层(展开缩写 + 中英双语词 + HyDE),根治机械分词的
P-A(2字母缩写被丢)/P-B(中文复合词被劈)。**claude 失败直接报错**(不静默回退老分词——
老路有 P-A/P-B bug,悄悄退回去=给坏结果还不吭声);只有 --no-understand(debug)能主动绕过。
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
        tps = main.execute("SELECT topic_id, relevance FROM source_topic WHERE paper_id=?",
                           (p["id"],)).fetchall()
        tline = ", ".join(f"{t['topic_id']}({t['relevance']:.0f})" for t in tps)
        tier = {"suspect": " ⚠️低可信", "flag": " (预印本)"}.get(p["quality_tier"] or "", "")
        print(f"{i}. [{h['score']:.3f}] {p['title']} ({p['year']}, {p['venue'] or '?'}){tier}")
        if tline:
            print(f"   主题: {tline}")
        print(f"   总结: storage/sources/{p['slug']}/  PDF: {p['source_path'] or '-'}\n")
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
    ap.add_argument("--no-understand", action="store_true",
                    help="[debug专用] 跳过 claude 问题理解层走老机械分词;正常跑别用(治不了缩写/中文复合词)")
    ap.add_argument("--mode", choices=["readall", "pipeline"], default="readall",
                    help="readall=全读(默认,库小:塞全部带总结的论文清单让一个 Opus 读+按需Read PDF);"
                         "pipeline=检索管道(方案A,大库:理解→混合召回→精排)")
    ap.add_argument("--topic", default=None, help="只在某主题范围内问(默认全库跨主题)")
    a = ap.parse_args()

    deep = a.answer or a.json
    # 全读模式不检索 → 不碰 fts/vec 索引;只有非全读路径或显式 --reindex 才建/增量索引
    if a.reindex or not (deep and a.mode == "readall"):
        reindex(force=a.reindex)
    if not a.question:
        if not a.reindex:
            ap.print_help()
        return

    if deep and a.mode == "readall":
        from retrieve import readall
        res = readall.run(a.question, topic=a.topic, limit=a.n)
        if a.json:
            print(json.dumps({"query": a.question, "mode": "readall",
                              "answerable": res["answerable"], "answer": res["text"],
                              "sources": res["sources"]}, ensure_ascii=False, indent=1))
        else:
            _show_answer(a.question, res)
        return

    understanding = None if a.no_understand else understand.understand_query(a.question)
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
