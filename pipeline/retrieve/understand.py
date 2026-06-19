"""问题理解层 —— 检索**前**把用户问题翻译成"干净的检索输入"。

为什么有这一层(2026-06-18,见 SESSION-2026-06-18-kb-retrieval.md 第三段):
  原来的 `search.parse_query` 机械切词有两个真 bug——P-A(2字母英文缩写如 "RL" 被正则丢)、
  P-B(单字停用词把中文复合词如"通用/应用"劈碎)。补正则补不完;改成在检索前让 claude 整体
  "听懂"问题,吐出干净的中英双语检索词 + 一段 HyDE 假想答案,根治这两类。
  Qwen 嵌入 + FTS 都不动,只是喂给它们的料更干净。

  输出 {"en_terms":[...], "zh_terms":[...], "hyde":"一段假想中文答案"}:
    - en_terms / zh_terms:同一概念给中英双语两版(库里标题/摘要英文、总结中文,两边都要命中)。
      → 交给 search.fts_rank(经 terms_to_fts,每词当原子短语,不再回炉 parse_query)。
    - hyde:论文总结口吻的假想答案 → 嵌入它(而非光问题)去跟库里真实中文总结比对,召回更准。

  claude 用不了 / 解析失败 → 返回 None,调用方(search.hybrid)自动回退老的 parse_query。
  整条问答流水线本就全靠 claude(打分/总结/核查),所以这层默认对所有查询都开。
"""
# --- path shim ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import json
import re

from lib.claude import run_claude
from lib.log import get_logger

log = get_logger("understand")

PROMPT = """你是一个学术论文检索系统的「问题理解」组件。库里是 AI / 机器学习方向的论文:\
标题和摘要是英文,结构化总结是中文。用户用中文或英文提一个研究问题,你要把它转成检索系统好用的输入。

用户问题:
{question}

只输出 JSON(不要任何解释、不要代码块标记):
{{
  "en_terms": [...],   // 英文检索词/短语,用来匹配英文标题和摘要
  "zh_terms": [...],   // 中文检索词/短语,用来匹配中文总结
  "hyde": "..."        // 一段假想的中文答案
}}

要求:
1. 抽出问题里的关键概念,每个概念都给英文和中文两个版本,分别进 en_terms / zh_terms。
2. 展开缩写:RL -> reinforcement learning(缩写本身也保留,论文里两种都出现)。
3. 补同义/相近说法:如「数字人」也给 virtual human / avatar。
4. 词要干净:每个元素是一个独立词或短语(2-5 个词),别塞整句、别带「的/和/是」这类虚词。
5. hyde:假装你已经知道答案,用中文写 2-4 句、论文总结口吻的「假想答案」,要具体、带术语\
(它会被向量化去跟库里真实总结比对,空话没用)。
6. 没把握别硬编:抽不出就少给几个词,不要编造库里不存在的概念。"""


def _parse(out):
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except Exception:
        return None
    en = [str(t).strip() for t in (o.get("en_terms") or []) if str(t).strip()]
    zh = [str(t).strip() for t in (o.get("zh_terms") or []) if str(t).strip()]
    hyde = (o.get("hyde") or "").strip()
    if not (en or zh):  # 一个词都没抽出来 = 等于没理解,让调用方回退
        return None
    return {"en_terms": en, "zh_terms": zh, "hyde": hyde}


def understand_query(question, timeout=90):
    """问题 -> {en_terms, zh_terms, hyde}。claude 失败/解析失败返回 None(调用方回退 parse_query)。"""
    try:
        out = run_claude(PROMPT.format(question=question), timeout=timeout)
    except Exception as e:  # noqa: BLE001  理解层绝不阻断检索,失败就回退老路
        log.info(f"理解层不可用(回退原始查询): {type(e).__name__}: {str(e)[:80]}")
        return None
    u = _parse(out)
    if u is None:
        log.info("理解层输出解析失败,回退原始查询")
        return None
    log.info(f"理解: en={len(u['en_terms'])} zh={len(u['zh_terms'])} hyde={len(u['hyde'])}字")
    return u
