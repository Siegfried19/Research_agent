"""Automated summarization: one `claude -p` call per paper (no agent/Workflow).
Inlines each paper's full text into the prompt, captures the Chinese structured
summary markdown from stdout, writes it to summary_path. Idempotent.
Usage: python3 pipeline/summarize_auto.py <topicId> [concurrency]
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from lib.db import ROOT
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log

MAX_CHARS = 120000
log = get_logger("summarize")


def full_text(w):
    tp = w.get("text_path")
    if tp and Path(tp).exists():
        t = Path(tp).read_text(encoding="utf-8", errors="ignore")
        if len(t.strip()) > 200:
            return t
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


def prompt(w, text):
    meta = f"{', '.join(w.get('authors') or [])} · {w.get('year')} · {w.get('venue') or ''} · 引用 {w.get('citation_count')} · DOI {w.get('doi') or w['id']}"
    return f"""你是论文精读员。请基于下面给出的论文全文,写一份**中文**结构化总结。

论文元信息:
- 标题: {w['title']}
- {meta}
- 与本研究主题的相关性评分: {w.get('relevance', '?')} ({w.get('relevance_reason') or ''})

要求:
- 全文中文(论文是英文/日语也读懂后用中文写),忠实原文、不编造数字。
- **直接输出下面这份 markdown 本身**,不要任何额外说明、不要代码围栏。
- 三段固定置顶(一句话 / 解决了什么问题 / 用什么方法解决的)。
- "局限与我的质疑"至少 3 条,既写作者自述局限,也写你自己的批判(方法是否站得住、实验是否充分、结论是否被过度解读、与"RL训练数字人与环境交互"主题相比的不足)。

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
## 局限与我的质疑

==== 论文全文如下 ====
{text}"""


def main():
    if len(sys.argv) < 2:
        print("usage: summarize_auto.py <topicId> [concurrency]", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    wl = json.loads((ROOT / "topics" / topic_id / "summarize_worklist.json").read_text(encoding="utf-8"))
    work = wl["work"]
    todo = [w for w in work if not Path(w["summary_path"]).exists()]
    log.info(f"summarize_auto: {len(work)} in worklist, {len(todo)} to do "
             f"({len(work) - len(todo)} already summarized), concurrency={concurrency}")

    def worker(w, _i):
        text = full_text(w)
        if not text:
            log.info(f"  SKIP [no text] {(w.get('title') or '')[:50]}")
            return {"error": "no text"}
        capped = text[:MAX_CHARS] + "\n...(全文过长,已截断)" if len(text) > MAX_CHARS else text
        md = run_claude(prompt(w, capped))
        if not md or len(md) < 200 or "## 一句话" not in md:
            raise RuntimeError(f"bad output ({len(md)} chars)")
        Path(w["summary_dir"]).mkdir(parents=True, exist_ok=True)
        Path(w["summary_path"]).write_text(md, encoding="utf-8")
        log.info(f"  OK   [{len(md) // 1024}KB] {(w.get('title') or '')[:50]}")
        return {"ok": True}

    res = pool(todo, worker, concurrency)
    ok = sum(1 for r in res if isinstance(r, dict) and r.get("ok"))
    fail = len(res) - ok
    log.info(f"summarize_auto done: {ok} ok, {fail} failed/skipped")
    run_log(topic_id, f"summarize_auto: {ok} ok, {fail} failed/skipped")


if __name__ == "__main__":
    main()
