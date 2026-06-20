"""Automated summarization: one `claude -p` call per paper (no agent/Workflow).
claude reads the paper's PDF directly via the Read tool (sees formulas/figures/
tables), captures the Chinese structured summary markdown from stdout, writes it
to summary_path. Idempotent. Papers with no PDF on disk are skipped and recorded
to topics/<id>/summarize_no_pdf.log (no plain-text fallback).
Usage: python3 pipeline/summarize/summarize_auto.py <topicId> [concurrency]
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT, open_db, now_iso
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log
from lib.store import paper_dir

log = get_logger("summarize")


def clean_output(md):
    """模型偶尔在 YAML front matter 前加一句寒暄(如"All 36 citations pass. Here is the summary.")。
    砍掉 front matter 之前的一切,保证总结以 `---\\npaper_id:` 开头(export/更新流程要解析这段头)。"""
    m = re.search(r"(?m)^---\s*$", md)
    if m and "paper_id:" in md[m.start():m.start() + 200]:
        return md[m.start():]
    return md


def quality_directive(w):
    """来源质量标记 -> 总结的批判强度。suspect=掠夺刊名单命中,开质疑模式。"""
    tier = w.get("quality_tier")
    sig = w.get("quality_signals") or ""
    if tier == "suspect":
        return f"""
⚠️ **来源警示(质疑模式)**: 该论文的期刊/出版商命中掠夺性名单({sig}),很可能未经过真实同行评审。本次总结按质疑模式写:
- 在标题下方的元信息引用行(以 "> " 开头那行)下面紧跟一行: `> ⚠️ **来源可疑**(掠夺刊名单命中):以下总结以批判视角撰写,结论未经可信同行评审,引用前需独立验证`
- 不要把论文的结论当作可信知识转述;每条"主要结果"都注明是"作者声称"。
- 所有方向性结论的 strength **一律封顶到 observed**(不得用 supported/strong);正文措辞相应压低。
- "局限与我的质疑"至少 5 条,主动找硬伤:方法描述是否含糊到无法复现、实验是否缺基线/消融、数据是否可疑(样本量、来源不明、图表异常)、是否大段套话或疑似拼凑、结论是否远超证据。
- 若读完判断这篇基本没有信息价值,在"一句话"里直说,不要硬找亮点。"""
    if tier == "flag":
        return "\n注意: 该论文为预印本或来源信息不全(未经同行评审确认)。正常总结,但在\"局限与我的质疑\"中注明这一点,对未经验证的结论保持保留。"
    return ""


def _template(w, version=1, note="首次总结"):
    """最终落盘的中文总结模板。version/note 由调用方给:首次=v1/首次总结;
    核查后重做=vN+1/核查后重做(见 resummarize)。2026-06-18 加"适用边界"一等段落。"""
    meta = f"{', '.join(w.get('authors') or [])} · {w.get('year')} · {w.get('venue') or ''} · 引用 {w.get('citation_count')} · DOI {w.get('doi') or w['id']}"
    return f"""---
paper_id: {w['id']}
version: {version}
based_on: []
created_at: {date.today().isoformat()}
note: {note}
---

# {w['title']}
> {meta}

## 一句话

## 解决了什么问题

## 用什么方法解决的（含直觉：为什么 work）

---

## 动机 & 背景
## 方法细节
## 数据集 & 实验设置
## 主要结果 & 结论（写方向，不堆精确数字）
## 适用边界（什么时候管用 / 什么时候不管用）
## 核心贡献
## 局限与我的质疑"""


def _resummary_block(prior_issues):
    """核查后重做(resummarize)时插在 prompt 顶部的避坑指令;首次总结(prior_issues=None)返回空串。
    设计要点(2026-06-18 取消修正环节裁决权):这是**从 PDF 重新写一份全新总结**,不是改旧版;
    问题清单只用来提醒避坑,**不许据此反推原文对错、不许照搬旧版措辞、不许写"已核对原文"类背书**——
    一切以你亲读 PDF 为准。这样根治旧 correct_summaries 那个"反向裁决核查员+伪造核对背书"的致命 bug。"""
    if not prior_issues:
        return ""
    lines = "\n".join(f"  - {i.get('problem', '')}(涉及:“{(i.get('quote') or '')[:80]}”)"
                      for i in prior_issues)
    return f"""
【为什么重做】这篇论文先前有一版总结,被一个**独立的跨模型事实核查员**对照 PDF 发现了下面这些问题:
{lines}
请你**从 PDF 重新写一份全新总结**(不是修改旧版,也不要照搬旧版的措辞或结构惯性)。上面的清单**只用来提醒你别重蹈覆辙**:
- **不要据这份清单反推原文到底是什么**——核查员也可能判错;一切以**你自己这次亲读 PDF** 为准。
- 凡你读到的与清单暗示的不一致,**信你读到的 PDF**,别迁就清单。
- **绝不要在总结里写"已核对原文""经核实"之类的话**——你的工作是忠实转写,不是给自己背书。

"""


def build_prompt(w, pdf_path, prior_issues=None, version=1, note="首次总结"):
    """单 agent 总结流程(2026-06-18 起去掉 note_plan/接地门,回到"边读边写"):
    通读 PDF → 写总结(数字让位 PDF、论断原子化+内联 strength) → 7问自查。
    prior_issues 非空 = 核查后重做(resummarize):顶部插避坑块,version/note 写进 frontmatter。"""
    meta = f"{', '.join(w.get('authors') or [])} · {w.get('year')} · {w.get('venue') or ''} · 引用 {w.get('citation_count')} · DOI {w.get('doi') or w['id']}"
    return f"""你是论文精读员。请**边读这份 PDF 边写**一份**中文**结构化总结。
{_resummary_block(prior_issues)}
【这份总结给谁看、干嘛用】首要读者是别的 AI agent(其次研究者本人):它检索到这篇时,靠你的总结判断"方法是什么、值不值得打开 PDF 深读"。判断轴:**正确性 > 可提取性 > 文笔**。精确数字/超参/确切公式不必给全——需要时读者按你给的出处去 PDF;你的任务是讲清**方法、直觉(为什么 work)、结果方向、什么时候管用**。

【铁律·只用本 PDF】总结里所有事实、数字、公式、方法细节**只能来自下面这份 PDF**;不要用你记忆里的相关知识填空,原文没写到的就写 `[原文未提]`,绝不脑补。这条只管"事实从哪来"——你的中文表达与写作能力照常发挥。
**反向也一样**:不要断言原文"没有/未包含/未给出"某内容(如"本文无附录""未给出超参""未做某消融")——**你没读到≠它不存在**(附录/补充材料/大表常在后几页);拿不准就别下这种"缺失"判断,需要的话回去把后面的页读完再说。

论文元信息:
- 标题: {w['title']}
- {meta}
- 与本研究主题的相关性评分: {w.get('relevance', '?')} ({w.get('relevance_reason') or ''})

【第一步·通读全文】用 Read 读取以下 PDF 的**全部页面**(多页论文;若超过 20 页用 pages 参数分批读完,不要只读前几页;**含正文之后的附录/补充材料/大表**):
{pdf_path}
你直读 PDF,能看到公式、图、表格(纯文本抽取会丢)。**读完再动笔,不要只读前几页就写。**

【第二步·写总结】严格用最下面的模板,中文:
- **每条论断写成能独立成立的原子句**(一句一个点,便于 agent 单独抽取)。
- **结果/方向性结论句末内联标 strength**:observed(只在部分任务/条件下观察到)|supported(有系统实验支撑)|strong(作者明确强主张且证据充分),没把握往低报;**措辞不许超过 strength**——observed 只能说"在 X 任务上更好",**不许**写成"全面/大幅超越";原文没证明泛化就别替它泛化。
- **数字克制 + 指向 PDF**:给量级或方向即可("提升约一个量级");确需写具体数值时**紧跟出处**("约 0.3,见 §5.2 表3"),且**不要把它当成总结的结论卖点**——精确值以 PDF 为准;不确定的数字宁可不写。
- **必须讲直觉**:为什么这个方法能 work(机制),而不只是罗列它做了什么。
- 准确转写关键数学公式(loss/目标函数/梯度更新/约束条件),不要因为是公式就跳过或含糊带过;重要图表说明它呈现了什么、支撑了什么结论。
- 引用关键原文时**加引号**(中文转述 + 括注英文原话或出处),让人能回 PDF 一眼定位。
- "适用边界"与"局限与我的质疑"分别写够(见模板):什么设定下管用/不管用;作者自述局限 + 你自己的批判(方法是否站得住、实验是否充分、结论是否被过度解读、与本研究主题相比的不足),至少 3 条。{quality_directive(w)}

【第三步·写完自查(逐条对照,不达标就回去补再定稿)】
1. 方向准确:每个结果方向(谁比谁好/稳不稳/有没有效)有没有写反或夸大(observed 写成全面超越)?
2. 直觉:讲清"为什么 work"了,还是只罗列做了什么?
3. 适用边界:什么时候管用/不管用、跟**强**基线还是弱基线比,说清了吗?
4. 接地 + 防张冠李戴:每条关键论断都能在 PDF 里找到依据吗?有没有把背景/被引工作(related work)的结果当成本文的?
5. 数字克制:有没有把孤立精确数字当结论卖点?该让位 PDF 的让位了(附了出处)吗?
6. 原子可提取:每条论断是不是独立成句、能被 agent 单独抽取?
7. 证明 vs 没证明:把论文真证明了的,和它没证明/留作未来工作的,分开说了吗?

输出要求:
- 完成(含自查修正)后,**只把中文总结 markdown 输出到 stdout**,不要任何额外说明、不要代码围栏。

输出模板:
{_template(w, version, note)}"""


def resummarize(work, concurrency=2, topic_id=None):
    """核查后重做(取代旧 correct_summaries 的打补丁):对每篇有 major 的论文,**从 PDF 重新写一份
    全新总结** vN+1——复用 build_prompt 整套机制(边读边写 + 7问自查),把上一版被核查
    发现的问题当**避坑提示**喂进去(无裁决权,见 _resummary_block:不许反推原文/不许照搬旧版/
    不许写"已核对"背书)。注册进 summary_versions,版本史保留。幂等(vN+1 已在则跳过)。
    无 PDF 跳过+记日志(同 sum:总结本就只从 PDF 写)。
    work: [{"paperId":.., "issues":[{quote,problem,severity}]}]; topic_id 用于带回相关性上下文。
    返回重做成功的条目列表。"""
    conn = open_db()
    todo = []
    for wk in work:
        if not wk.get("issues"):
            continue
        if topic_id:
            p = conn.execute(
                """SELECT p.*, pt.relevance, pt.relevance_reason FROM papers p
                     LEFT JOIN paper_topic pt ON pt.paper_id=p.id AND pt.topic_id=?
                    WHERE p.id=?""", (topic_id, wk["paperId"])).fetchone()
        else:
            p = conn.execute("SELECT * FROM papers WHERE id=?", (wk["paperId"],)).fetchone()
        if not p:
            log.info(f"skip (not in db): {wk['paperId']}")
            continue
        cur = conn.execute(
            "SELECT version FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1",
            (wk["paperId"],)).fetchone()
        if not cur:
            log.info(f"skip (no summary): {wk['paperId']}")
            continue
        nv = cur["version"] + 1
        sdir = paper_dir(p["slug"])
        out = sdir / f"v{nv}.md"
        if out.exists():
            log.info(f"skip (v{nv} exists): {(p['title'] or '')[:50]}")
            continue
        todo.append({"w": dict(p), "issues": wk["issues"], "nextVersion": nv,
                     "summary_dir": str(sdir), "outPath": str(out)})
    conn.close()
    log.info(f"resummarize: {len(work)} flagged, {len(todo)} to redo, concurrency={concurrency}")

    def worker(t, _i):
        w = t["w"]
        pp = w.get("pdf_path")
        pdf_abs = None
        if pp:
            cand = Path(pp) if Path(pp).is_absolute() else ROOT / pp
            if cand.exists():
                pdf_abs = str(cand.resolve())
        if not pdf_abs:
            # 同 sum:无 PDF 不回退,记一条日志跳过(summarized 篇丢了 PDF = 异常)。
            log.info(f"  SKIP [no pdf] {(w.get('title') or '')[:50]}")
            return {"error": "no pdf"}
        nv = t["nextVersion"]
        Path(t["summary_dir"]).mkdir(parents=True, exist_ok=True)
        prompt = build_prompt(w, pdf_abs, prior_issues=t["issues"],
                              version=nv, note=f"核查后重做(避开 {len(t['issues'])} 处问题)")
        md = clean_output(run_claude(prompt, tools=["Read"], timeout=1200))
        if not md or len(md) < 200 or not md.startswith("---") or "## 一句话" not in md:
            raise RuntimeError(f"bad output ({len(md)} chars)")
        Path(t["outPath"]).write_text(md, encoding="utf-8")
        log.info(f"  OK v{nv} [pdf, {len(md) // 1024}KB] {(w.get('title') or '')[:50]}")
        return t

    res = pool(todo, worker, concurrency)
    done = [r for r in res if isinstance(r, dict) and r.get("outPath") and Path(r["outPath"]).exists()]

    conn = open_db()
    for t in done:
        rel = str(Path(t["outPath"]).relative_to(ROOT))
        conn.execute(
            """INSERT OR IGNORE INTO summary_versions (paper_id,version,path,based_on,note,created_at)
               VALUES (?,?,?,?,?,?)""",
            (t["w"]["id"], t["nextVersion"], rel, "[]",
             f"核查后重做(核查发现 {len(t['issues'])} 处问题,从 PDF 重写)", now_iso()))
        conn.execute("UPDATE papers SET summarized_at=? WHERE id=?", (now_iso(), t["w"]["id"]))
    conn.commit()
    conn.close()
    log.info(f"resummarize done: {len(done)}/{len(todo)} redone+registered")
    run_log(topic_id or "-", f"resummarize: {len(done)}/{len(todo)} redone")
    return done


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
        Path(w["summary_path"]).parent.mkdir(parents=True, exist_ok=True)
        prompt = build_prompt(w, pdf_abs)
        # 多页 PDF + 7问自查,turn 数比一次性多,超时放宽到 1200s。只需 Read 读 PDF。
        md = clean_output(run_claude(prompt, tools=["Read"], timeout=1200))
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
