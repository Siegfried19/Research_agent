"""Automated summarization: one `claude -p` call per paper (no agent/Workflow).
claude reads the paper's PDF directly via the Read tool (sees formulas/figures/
tables), captures the Chinese structured summary markdown from stdout, writes it
to summary_path. Idempotent. Papers with no PDF on disk are skipped and recorded
to topics/<id>/summarize_no_pdf.log (no plain-text fallback).
Usage: python3 pipeline/stages/summarize_auto.py <topicId> [concurrency]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT, load_config
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log

log = get_logger("summarize")

# 接地门开关(config summarize.grounding_gate,默认开)。开=写正文前 agent 先列 note_plan
# 再跑 tools/grounding_gate.py 机械核对引文真在 PDF 里,钉不住打回重写;关=只列 note_plan 不验门。
GATE_ON = bool((load_config().get("summarize") or {}).get("grounding_gate", True))
GATE_SCRIPT = ROOT / "pipeline" / "tools" / "grounding_gate.py"


def _text_from_pdf(w):
    pp = w.get("pdf_path")
    if pp and Path(pp).exists():
        try:
            tmp = Path(tempfile.gettempdir()) / f"sum_{os.getpid()}_{abs(hash(w['id']))}.txt"
            subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", pp, str(tmp)], timeout=60, check=False)
            t = tmp.read_text(encoding="utf-8", errors="ignore")
            tmp.unlink(missing_ok=True)
            if len(t.strip()) > 200:
                return t
        except Exception:
            pass
    return None


def clean_output(md):
    """模型偶尔在 YAML front matter 前加一句寒暄(如"All 36 citations pass. Here is the summary.")。
    砍掉 front matter 之前的一切,保证总结以 `---\\npaper_id:` 开头(export/更新流程要解析这段头)。"""
    m = re.search(r"(?m)^---\s*$", md)
    if m and "paper_id:" in md[m.start():m.start() + 200]:
        return md[m.start():]
    return md


def full_text(w):
    """对 PDF 跑 pdftotext 抽出纯文本(临时文件,用完即删)。sum 阶段直读 PDF 不用它,
    但 verify_summaries 的省钱模式(codex_self_render=false)仍 import 它把原文喂给核查模型。
    PDF 是唯一原文来源(2026-06-16 起不再有 store/text);抽不出返回 None。"""
    return _text_from_pdf(w)


def quality_directive(w):
    """来源质量标记 -> 总结的批判强度。suspect=掠夺刊名单命中,开质疑模式。"""
    tier = w.get("quality_tier")
    sig = w.get("quality_signals") or ""
    if tier == "suspect":
        return f"""
⚠️ **来源警示(质疑模式)**: 该论文的期刊/出版商命中掠夺性名单({sig}),很可能未经过真实同行评审。本次总结按质疑模式写:
- 在标题下方的元信息引用行(以 "> " 开头那行)下面紧跟一行: `> ⚠️ **来源可疑**(掠夺刊名单命中):以下总结以批判视角撰写,结论未经可信同行评审,引用前需独立验证`
- 不要把论文的结论当作可信知识转述;每条"主要结果"都注明是"作者声称"。
- note_plan 里所有 strength **一律封顶到 observed**(不得用 supported/strong);正文措辞相应压低。
- "局限与我的质疑"至少 5 条,主动找硬伤:方法描述是否含糊到无法复现、实验是否缺基线/消融、数据是否可疑(样本量、来源不明、图表异常)、是否大段套话或疑似拼凑、结论是否远超证据。
- 若读完判断这篇基本没有信息价值,在"一句话"里直说,不要硬找亮点。"""
    if tier == "flag":
        return "\n注意: 该论文为预印本或来源信息不全(未经同行评审确认)。正常总结,但在\"局限与我的质疑\"中注明这一点,对未经验证的结论保持保留。"
    return ""


def _template(w):
    """最终落盘的中文总结模板(自始未变)。note_plan 是中间脚手架,不进这份产出。"""
    meta = f"{', '.join(w.get('authors') or [])} · {w.get('year')} · {w.get('venue') or ''} · 引用 {w.get('citation_count')} · DOI {w.get('doi') or w['id']}"
    return f"""---
paper_id: {w['id']}
version: 1
based_on: []
created_at: {date.today().isoformat()}
note: 首次总结
---

# {w['title']}
> {meta}

## 一句话

## 解决了什么问题

## 用什么方法解决的

---

## 动机 & 背景
## 方法细节
## 数据集 & 实验设置
## 主要结果 & 结论
## 核心贡献
## 局限与我的质疑"""


def _gate_block(note_plan_path, pdf_path):
    """接地门那段指令;开关关闭时返回空串。"""
    if not GATE_ON:
        return ""
    cmd = f'python3 "{GATE_SCRIPT}" "{note_plan_path}" "{pdf_path}"'
    return f"""【第二步半·接地门(必过)】note_plan 写好后,用 Bash 运行下面这条命令,机械核对每条引文是否真在 PDF 里:
  {cmd}
它输出 JSON,只有 `"all_pass": true` 才算过。若有钉不住的条目(fails 列表),**逐条修正 note_plan**:找对原文引文 / 把该条 strength 降级 / 实在原文没有就把它从 note_plan 删掉(对应内容也不要写进总结)。改完**重跑该命令**,直到 all_pass=true。最多修 2 轮;2 轮后仍钉不住的条目直接删、不写进正文。
"""


def build_prompt(w, pdf_path, note_plan_path):
    """单 agent 总结流程:知识隔离 → 读全文 → 列 note_plan → (接地门) → 写总结 → 7问自查。"""
    meta = f"{', '.join(w.get('authors') or [])} · {w.get('year')} · {w.get('venue') or ''} · 引用 {w.get('citation_count')} · DOI {w.get('doi') or w['id']}"
    return f"""你是论文精读员。请按下面步骤,写一份**中文**结构化总结。

【铁律·只用本 PDF】总结里所有事实、数字、公式、方法细节**只能来自下面这份 PDF**;不要用你记忆里的相关知识填空,原文没写到的就写 `[原文未提]`,绝不脑补。这条只管"事实从哪来"——你的中文表达与写作能力照常发挥。
**反向也一样**:不要断言原文"没有/未包含/未给出"某内容(如"本文无附录""未给出超参""未做某消融")——**你没读到≠它不存在**(附录/补充材料/大表常在后几页);拿不准就别下这种"缺失"判断,需要的话回去把后面的页读完再说。

论文元信息:
- 标题: {w['title']}
- {meta}
- 与本研究主题的相关性评分: {w.get('relevance', '?')} ({w.get('relevance_reason') or ''})

【第一步·读全文】用 Read 读取以下 PDF 的**全部页面**(多页论文;若超过 20 页用 pages 参数分批读完,不要只读前几页;**含正文之后的附录/补充材料/大表**):
{pdf_path}
你直读 PDF,能看到公式、图、表格(纯文本抽取会丢)。

【第二步·列 note_plan】动笔写正文前,先把要写进总结的每一条具体事实拆成"锚点",用 Write 写到这个文件(一个 JSON 数组):
{note_plan_path}
每条:
{{ "kind": "method|result|contribution",
   "point": "要写进总结的那句话(中文)",
   "quote_en": "支撑它的原文片段(英文原话**逐字照抄**,会加引号进正文)",
   "where": "出处,如 p.5 §3.2 / 表2 / 图3",
   "strength": "result/contribution 才填 observed|supported|strong;method 填 null" }}
- 每个具体数字、每个关键方法点、每条作者声称的贡献,都要有一条;`quote_en` 必须是 PDF 里**真实存在的原话**(逐字照抄,别意译、别把几处拼接成一句)。
- strength 按原文证据强度:只在部分任务/条件下观察到=observed,有系统实验支撑=supported,作者明确强主张且证据充分=strong。**没把握就往低报。**

{_gate_block(note_plan_path, pdf_path)}
【第三步·写总结】严格用最下面的模板,把 note_plan 的锚点织进正文:
- 涉及具体事实/数字处**引原文加引号**(中文转述 + 括注英文原话或出处),让人能回 PDF 一眼定位。
- **措辞不许超过 strength**:observed 的结果只能说"在 X 任务上更好",**不许**写成"全面/大幅超越";原文没证明泛化就别替它泛化。
- 准确转写关键数学公式(loss/目标函数/梯度更新/约束条件),不要因为是公式就跳过或含糊带过;重要图表说明它呈现了什么、支撑了什么结论。
- 忠实原文、不编造数字。
- "局限与我的质疑"至少 3 条,既写作者自述局限,也写你自己的批判(方法是否站得住、实验是否充分、结论是否被过度解读、与本研究主题相比的不足)。{quality_directive(w)}

【第四步·写完自查(7 问,逐条对照,不达标就回去补再定稿)】
1. 证据链:每条主要结果都有对应的 note_plan 锚点(数字/出处)吗?
2. 关键数字:核心指标、提升幅度、数据规模有没有遗漏?
3. 机制↔结果:有没有讲清"为什么这个方法能 work",而不是只罗列结果数字?
4. 强基线:写的是它跟**强**基线/SOTA 比的结果,而非只挑弱基线吗?
5. 机制性讨论:讨论部分是在解释原因,而不是复述结果吗?
6. 证明 vs 没证明:把论文真证明了的,和它没证明/留作未来工作的,分开说了吗?
7. 复用要点:对想复用此方法的人,关键细节(超参/结构/数据条件)够具体吗?

输出要求:
- 完成(含自查修正)后,**只把第三步的中文总结 markdown 输出到 stdout**(note_plan 已在文件里,不要出现在 stdout),不要任何额外说明、不要代码围栏。

输出模板:
{_template(w)}"""


def main():
    if len(sys.argv) < 2:
        print("usage: summarize_auto.py <topicId> [concurrency] [--limit N]", file=sys.stderr)
        sys.exit(1)
    # --limit N: only summarize the first N still-to-do papers this run (worklist
    # is rank-ordered, so this takes the highest-ranked unsummarized). Idempotent
    # across runs — the next run picks up where this one stopped. Used by the
    # nightly cron to cap each batch (e.g. ~10/run) so it fits one token window.
    limit = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        limit = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    topic_id = sys.argv[1]
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 2  # PDF 模式更重,默认调小
    wl = json.loads((ROOT / "topics" / topic_id / "summarize_worklist.json").read_text(encoding="utf-8"))
    work = wl["work"]
    todo = [w for w in work if not Path(w["summary_path"]).exists()]
    if limit is not None:
        todo = todo[:limit]
    log.info(f"summarize_auto: {len(work)} in worklist, {len(todo)} to do this run"
             f"{f' (capped to {limit})' if limit is not None else ''}, concurrency={concurrency}")

    no_pdf_log = ROOT / "topics" / topic_id / "summarize_no_pdf.log"

    def log_no_pdf(w):
        # 一行一条:时间戳 \t DOI/id \t 标题。append 模式,单行短写在 POSIX 上原子,并发安全。
        line = f"{datetime.now().isoformat(timespec='seconds')}\t{w.get('doi') or w.get('id') or ''}\t{w.get('title') or ''}\n"
        with no_pdf_log.open("a", encoding="utf-8") as f:
            f.write(line)

    def worker(w, _i):
        pp = w.get("pdf_path")
        pdf_abs = None
        if pp:
            cand = Path(pp) if Path(pp).is_absolute() else ROOT / pp
            if cand.exists():
                pdf_abs = str(cand.resolve())
        if not pdf_abs:
            # 无 PDF:不再回退纯文本,只记一条失败日志(时间+DOI+标题)并跳过。
            log_no_pdf(w)
            log.info(f"  SKIP [no pdf] {(w.get('title') or '')[:50]}")
            return {"error": "no pdf"}
        # note_plan 落在 summary_dir(持久化,供 verify 复用);先建目录,agent 才能 Write/Bash。
        summary_dir = Path(w["summary_dir"])
        summary_dir.mkdir(parents=True, exist_ok=True)
        note_plan_path = (summary_dir / "note_plan.json").resolve()
        # 工具:Read 看 PDF、Write 落 note_plan;接地门开时再给 Bash(只许 python3 跑门脚本)。
        tools = ["Read", "Write"] + (["Bash(python3:*)"] if GATE_ON else [])
        prompt = build_prompt(w, pdf_abs, str(note_plan_path))
        # 多页 PDF + note_plan + 接地门循环 + 7问自查,turn 数比一次性多,超时放宽到 1200s。
        md = run_claude(prompt, tools=tools, timeout=1200)
        md = clean_output(md)
        if not md or len(md) < 200 or not md.startswith("---") or "## 一句话" not in md:
            raise RuntimeError(f"bad output ({len(md)} chars)")
        Path(w["summary_path"]).write_text(md, encoding="utf-8")
        log.info(f"  OK   [pdf, {len(md) // 1024}KB] {(w.get('title') or '')[:50]}")
        return {"ok": True}

    res = pool(todo, worker, concurrency)
    ok = sum(1 for r in res if isinstance(r, dict) and r.get("ok"))
    fail = len(res) - ok
    log.info(f"summarize_auto done: {ok} ok, {fail} failed/skipped")
    run_log(topic_id, f"summarize_auto: {ok} ok, {fail} failed/skipped")


if __name__ == "__main__":
    main()
