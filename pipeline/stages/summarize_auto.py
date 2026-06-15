"""Automated summarization: one `claude -p` call per paper (no agent/Workflow).
claude reads the paper's PDF directly via the Read tool (sees formulas/figures/
tables), captures the Chinese structured summary markdown from stdout, writes it
to summary_path. Idempotent. Papers with no PDF on disk are skipped and recorded
to topics/<id>/summarize_no_pdf.log (no plain-text fallback).
Usage: python3 pipeline/stages/summarize_auto.py <topicId> [concurrency]
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log

log = get_logger("summarize")


def _text_from_file(w):
    tp = w.get("text_path")
    if tp and Path(tp).exists():
        t = Path(tp).read_text(encoding="utf-8", errors="ignore")
        if len(t.strip()) > 200:
            return t
    return None


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


def full_text(w, prefer_pdf=False):
    """抽出论文纯文本。sum 阶段已不用它,但 verify_summaries / correct_summaries 仍 import 它,
    把原文喂给核查/修正模型。prefer_pdf=True 时优先对 PDF 跑 pdftotext(让核查者和撰写者
    读同一份 PDF),抽不到再退已存的 text_path;默认相反(text_path 优先,无则 pdftotext)。"""
    order = (_text_from_pdf, _text_from_file) if prefer_pdf else (_text_from_file, _text_from_pdf)
    for fn in order:
        t = fn(w)
        if t:
            return t
    return None


def quality_directive(w):
    """来源质量标记 -> 总结的批判强度。suspect=掠夺刊名单命中,开质疑模式。"""
    tier = w.get("quality_tier")
    sig = w.get("quality_signals") or ""
    if tier == "suspect":
        return f"""
⚠️ **来源警示(质疑模式)**: 该论文的期刊/出版商命中掠夺性名单({sig}),很可能未经过真实同行评审。本次总结按质疑模式写:
- 在标题下方的元信息引用行(以 "> " 开头那行)下面紧跟一行: `> ⚠️ **来源可疑**(掠夺刊名单命中):以下总结以批判视角撰写,结论未经可信同行评审,引用前需独立验证`
- 不要把论文的结论当作可信知识转述;每条"主要结果"都注明是"作者声称"。
- "局限与我的质疑"至少 5 条,主动找硬伤:方法描述是否含糊到无法复现、实验是否缺基线/消融、数据是否可疑(样本量、来源不明、图表异常)、是否大段套话或疑似拼凑、结论是否远超证据。
- 若读完判断这篇基本没有信息价值,在"一句话"里直说,不要硬找亮点。"""
    if tier == "flag":
        return "\n注意: 该论文为预印本或来源信息不全(未经同行评审确认)。正常总结,但在\"局限与我的质疑\"中注明这一点,对未经验证的结论保持保留。"
    return ""


def _instructions(w):
    meta = f"{', '.join(w.get('authors') or [])} · {w.get('year')} · {w.get('venue') or ''} · 引用 {w.get('citation_count')} · DOI {w.get('doi') or w['id']}"
    return f"""你是论文精读员。请写一份**中文**结构化总结。

论文元信息:
- 标题: {w['title']}
- {meta}
- 与本研究主题的相关性评分: {w.get('relevance', '?')} ({w.get('relevance_reason') or ''})

要求:
- 全文中文(论文是英文/日语也读懂后用中文写),忠实原文、不编造数字。
- **直接输出下面这份 markdown 本身**,不要任何额外说明、不要代码围栏。
- 三段固定置顶(一句话 / 解决了什么问题 / 用什么方法解决的)。
- "局限与我的质疑"至少 3 条,既写作者自述局限,也写你自己的批判(方法是否站得住、实验是否充分、结论是否被过度解读、与本研究主题相比的不足)。{quality_directive(w)}

输出模板:
---
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


def prompt_pdf(w, pdf_path):
    """直读 PDF 模式:让 claude 用 Read 工具看 PDF(能看到公式/图/表,纯文本抽取会丢)。"""
    return _instructions(w) + f"""

==== 论文 PDF ====
用 Read 工具读取以下 PDF 的**全部页面**(多页论文;若超过 20 页用 pages 参数分批读完,不要只读前几页):
{pdf_path}

你直接读 PDF,能看到公式、图、表格——总结时务必:
- 准确转写关键数学公式(loss/目标函数/梯度更新/约束条件等),不要因为是公式就跳过或含糊带过;
- 说明重要图表(架构图/实验曲线/对比表格)呈现了什么、支撑了什么结论;
- 忠实原文、不编造数字。"""


def main():
    if len(sys.argv) < 2:
        print("usage: summarize_auto.py <topicId> [concurrency]", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 2  # PDF 模式更重,默认调小
    wl = json.loads((ROOT / "topics" / topic_id / "summarize_worklist.json").read_text(encoding="utf-8"))
    work = wl["work"]
    todo = [w for w in work if not Path(w["summary_path"]).exists()]
    log.info(f"summarize_auto: {len(work)} in worklist, {len(todo)} to do "
             f"({len(work) - len(todo)} already summarized), concurrency={concurrency}")

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
        # 直读 PDF:claude 用 Read 看公式/图/表;读多页+图像 token 多,故超时放宽
        md = run_claude(prompt_pdf(w, pdf_abs), tools=["Read"], timeout=900)
        if not md or len(md) < 200 or "## 一句话" not in md:
            raise RuntimeError(f"bad output ({len(md)} chars)")
        Path(w["summary_dir"]).mkdir(parents=True, exist_ok=True)
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
