"""核查态读取/解析(纯 stdlib)。

verify 阶段把每篇核查结论落进 `topics/<id>/verify_status.json`（`{paper_id:{verdict,version}}`）。
这里把它汇总 + 解析成"出口用的态"。**单一真相源**：库地图(map.py) 和问答(retrieve/answer.py)
都从这里读,标记口径一致。纯 stdlib,不引 claude/torch,可在任意 python3 / 只读挂载点上跑。
"""
import json

from .db import ROOT


def load_verify_status():
    """汇总全库各 topic 的 verify_status.json → {paper_id: {verdict, version}};
    同篇多 topic 取最高 version(最近一次核查)。"""
    agg = {}
    for sp in (ROOT / "topics").glob("*/verify_status.json"):
        try:
            for pid, st in json.loads(sp.read_text(encoding="utf-8")).items():
                cur = agg.get(pid)
                if not cur or (st.get("version") or 0) > (cur.get("version") or 0):
                    agg[pid] = st
        except Exception:
            continue
    return agg


def resolve_verify(status_map, paper_id, cur_version):
    """把"核查记录 vs 当前最高版"解析成出口用的态:
    无总结→None;无记录→unverified;记录版本<当前→stale(新版没核);否则=记录的 verdict
    (pass/minor/major/unverifiable)。"""
    if cur_version is None:
        return None
    st = status_map.get(paper_id)
    if not st:
        return "unverified"
    if (st.get("version") or 0) < cur_version:
        return "stale"
    return st.get("verdict")
