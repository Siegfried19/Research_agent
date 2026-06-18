"""出口的"回答"层(借 PaperQA2 + Self-RAG + CRAG 的可靠性纪律):
- 闭集引用:只能引召回里的 [n],禁止编不存在的来源/DOI。
- 会说不知道:没有相关证据 → 直接出"库里没有"哨兵(空候选时不调 LLM,确定性短路)。
- 自检(可选):再过一遍,逐句核证据是否支撑,撑不住的删/标。
- quality_tier 透传:suspect 来源标 ⚠️,答案里显式说明来源可疑。

产出同时服务 --answer(给人看的带引用中文回答) 和 --json(给外部 agent 的机器可读)。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from lib.db import open_db, ROOT
from lib.claude import run_claude
from lib.log import get_logger

log = get_logger("answer")
CANNOT = "库里没有相关内容。"

TIER_NOTE = {"suspect": " ⚠️低可信来源(掠夺刊嫌疑,引用需核实)", "flag": " (预印本,未同行评审)"}

ANSWER_PROMPT = """你是论文库问答助手。**只用下面提供的证据**回答问题,引用时在句末标来源编号 [n]。
- 只能引下面列出的编号,**绝不**编造其它来源或 DOI。
- 标了 ⚠️低可信来源 的材料,引用时必须显式说明来源可疑。
- 证据撑不起答案就回:"{cannot}" —— 不要用证据外的知识硬答。
- 中文,简洁,有据。

## 问题
{q}

## 证据(每条带编号)
{ctx}

## 回答"""


def _latest_summary_path(main, paper_id):
    """从 DB summary_versions 取最高版本的总结路径(权威源,与 index/search/rerank 一致;
    不再扫磁盘 glob——那会在 v10+ 因字符串排序误取 v9,且可能和 DB 不一致)。"""
    r = main.execute("SELECT path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1",
                     (paper_id,)).fetchone()
    if not r:
        return None
    fp = ROOT / r["path"]
    return str(fp) if fp.exists() else None


def _source_row(main, r):
    """ranked 里一条 → 结构化来源 dict(给 --json + 引用映射)。"""
    p = r["paper"]
    return {
        "doi": p["doi"], "title": p["title"], "year": p["year"], "venue": p["venue"],
        "quality_tier": p["quality_tier"],
        "rcs_score": r.get("rcs", {}).get("score"),
        "summary_path": _latest_summary_path(main, p["id"]),
        "pdf_path": str(ROOT / p["pdf_path"]) if p["pdf_path"] else None,
    }


def build(question, ranked):
    """生成回答 + 结构化来源。返回 {answerable, text, sources}。"""
    if not ranked:
        return {"answerable": False, "text": CANNOT, "sources": []}

    main = open_db()
    blocks, sources = [], []
    for i, r in enumerate(ranked, 1):
        p = r["paper"]
        note = TIER_NOTE.get(p["quality_tier"] or "", "")
        ev = r.get("rcs", {}).get("evidence") or ""
        blocks.append(f"[{i}] {p['title']} ({p['year']}, {p['venue'] or '?'}){note}\n{ev}")
        sources.append({"n": i, **_source_row(main, r)})
    main.close()

    text = run_claude(
        ANSWER_PROMPT.format(cannot=CANNOT, q=question, ctx="\n\n".join(blocks)),
        timeout=300).strip()
    answerable = CANNOT[:6] not in text  # 命中哨兵 → 答不了
    return {"answerable": answerable, "text": text, "sources": sources}
