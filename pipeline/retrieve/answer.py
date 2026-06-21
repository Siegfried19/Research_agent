"""出口的"回答"层(借 PaperQA2 + Self-RAG + CRAG 的可靠性纪律):
- 闭集引用:只能引召回里的 [n],禁止编不存在的来源/DOI。
- 会说不知道:没有相关证据 → 直接出"库里没有"哨兵(空候选时不调 LLM,确定性短路)。
- 自检(可选):再过一遍,逐句核证据是否支撑,撑不住的删/标。
- quality_tier 透传:suspect 来源标 ⚠️,答案里显式说明来源可疑。
- verify 核查态透传(2026-06-18):像 quality_tier 一样**只标注不过滤**——major(核查发现
  重大问题)/stale(总结已更新但新版未核查)在答案里 ⚠️ 标出;完整态进 --json 供 agent 自决。

产出同时服务 --answer(给人看的带引用中文回答) 和 --json(给外部 agent 的机器可读)。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from lib.db import open_db, ROOT
from lib.claude import run_claude
from lib.log import get_logger
from lib.verify_status import load_verify_status, resolve_verify  # 单一真相源,与 map.py 共用

log = get_logger("answer")
CANNOT = "库里没有相关内容。"

TIER_NOTE = {"suspect": " ⚠️低可信来源(掠夺刊嫌疑,引用需核实)", "flag": " (预印本,未同行评审)"}
# 核查态里只有这两类会污染"该版本可不可信",答案中显式 ⚠️;其余(pass/minor/unverifiable/
# unverified)不污染判断,只进 --json 不打扰回答。
VERIFY_NOTE = {"major": " ⚠️核查发现重大问题(疑方向反转/张冠李戴/过度声称,引用须核实)",
               "stale": " ⚠️总结已更新,新版尚未核查"}

ANSWER_PROMPT = """你是论文库问答助手。**只用下面提供的证据**回答问题,引用时在句末标来源编号 [n]。
- 只能引下面列出的编号,**绝不**编造其它来源或 DOI。
- 标了 ⚠️低可信来源 的材料,引用时必须显式说明来源可疑。
- 标了 ⚠️核查发现重大问题 或 ⚠️总结已更新…未核查 的材料,引用时必须提示该结论尚待核实。
- 证据撑不起答案就回:"{cannot}" —— 不要用证据外的知识硬答。
- 中文,简洁,有据。

## 问题
{q}

## 证据(每条带编号)
{ctx}

## 回答"""


def _latest_version(main, paper_id):
    """DB 里该论文最高总结版本号 (version, path);无总结返回 (None, None)。权威源,
    与 index/search/rerank 一致;不扫磁盘 glob(会在 v10+ 因字符串排序误取 v9)。"""
    r = main.execute("SELECT version, path FROM summary_versions WHERE paper_id=? "
                     "ORDER BY version DESC LIMIT 1", (paper_id,)).fetchone()
    return (r["version"], r["path"]) if r else (None, None)


def make_source(main, status_map, paper, rcs=None):
    """一个 sources 行(+可选 rcs) → 出口用结构化来源 dict。**共享契约层**:
    readall(全读) 和 pipeline(检索) 两条出口都用它拼 --json 的 sources,保证字段/标记口径一致。"""
    p = paper
    ver, path = _latest_version(main, p["id"])
    fp = ROOT / path if path else None
    return {
        "doi": p["doi"], "title": p["title"], "year": p["year"], "venue": p["venue"],
        "quality_tier": p["quality_tier"],
        "verify_status": resolve_verify(status_map, p["id"], ver),
        "summary_version": ver,
        "rcs_score": (rcs or {}).get("score"),
        "summary_path": str(fp) if fp and fp.exists() else None,
        "source_path": str(ROOT / p["source_path"]) if p["source_path"] else None,
    }


def _source_row(main, status_map, r):
    """ranked 里一条 → 结构化来源 dict(给 --json + 引用映射)。"""
    return make_source(main, status_map, r["paper"], r.get("rcs"))


def build(question, ranked):
    """生成回答 + 结构化来源。返回 {answerable, text, sources}。"""
    if not ranked:
        return {"answerable": False, "text": CANNOT, "sources": []}

    main = open_db()
    status_map = load_verify_status()
    blocks, sources = [], []
    for i, r in enumerate(ranked, 1):
        p = r["paper"]
        src = _source_row(main, status_map, r)
        note = TIER_NOTE.get(p["quality_tier"] or "", "") + VERIFY_NOTE.get(src["verify_status"] or "", "")
        ev = r.get("rcs", {}).get("evidence") or ""
        blocks.append(f"[{i}] {p['title']} ({p['year']}, {p['venue'] or '?'}){note}\n{ev}")
        sources.append({"n": i, **src})
    main.close()

    text = run_claude(
        ANSWER_PROMPT.format(cannot=CANNOT, q=question, ctx="\n\n".join(blocks)),
        timeout=300).strip()
    answerable = CANNOT[:6] not in text  # 命中哨兵 → 答不了
    return {"answerable": answerable, "text": text, "sources": sources}
