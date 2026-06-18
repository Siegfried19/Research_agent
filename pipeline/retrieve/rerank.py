"""RCS 精挑(Reranking + Contextual Summarization,借 PaperQA2):
混合召回拿到一批候选后,让 claude -p 逐篇"针对这个问题"重判相关性(0-10)+抽相关证据。
0 分=不相关,丢弃;按分排序留 top-K。把"召回"变"精排",顺带把总结压成"针对问题的证据"。

我们是 summary-first:候选已是 curated 总结(压缩离线做好了),所以这里只做"按问题重打分+抽证据"
这半步 —— PaperQA2 消融证明这半步是关键(去掉 RCS 准确率显著掉,p<0.001)。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import json
import re

from lib.db import open_db, ROOT
from lib.claude import run_claude, pool
from lib.log import get_logger

log = get_logger("rerank")

PROMPT = """你在帮一个论文库回答问题。下面是一篇论文的中文总结。请**只针对这个问题**判断它有没有用,并抽出相关证据。

问题:{q}

论文总结:
{body}

只输出 JSON(别的都不要):
{{"score": <0-10 整数,与问题相关度,完全不相关给 0>, "evidence": "<从总结里抽出的、与问题相关的要点,保留具体数字/方法名;不相关留空>"}}"""


def latest_summary_text(main, paper_id):
    r = main.execute("SELECT path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1",
                     (paper_id,)).fetchone()
    if not r:
        return None
    fp = ROOT / r["path"]
    return fp.read_text(encoding="utf-8", errors="replace") if fp.exists() else None


def _parse(out):
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return {"score": 0, "evidence": ""}
    try:
        o = json.loads(m.group(0))
        return {"score": int(float(o.get("score", 0))), "evidence": (o.get("evidence") or "").strip()}
    except Exception:
        return {"score": 0, "evidence": ""}


def rcs_rerank(question, hits, keep=8, limit=4, max_chars=12000):
    """对 search.hybrid 的候选做 RCS。返回带 'rcs'={score,evidence} 的 top-keep,按分降序。"""
    main = open_db()
    cand = []
    for h in hits:
        body = latest_summary_text(main, h["paper"]["id"])
        if not body:  # 没总结的用摘要/标题顶
            body = h["paper"]["abstract"] or h["paper"]["title"] or ""
        cand.append((h, body[:max_chars]))
    main.close()

    def worker(item, i):
        h, body = item
        return _parse(run_claude(PROMPT.format(q=question, body=body), timeout=120))

    scored = pool(cand, worker, limit=limit)
    out = []
    for (h, _b), s in zip(cand, scored):
        if isinstance(s, dict) and not s.get("error") and s.get("score", 0) > 0:
            out.append({**h, "rcs": s})
    out.sort(key=lambda x: -x["rcs"]["score"])
    log.info(f"RCS: {len(hits)} 候选 → {len(out)} 相关(留前 {min(keep,len(out))})")
    return out[:keep]
