"""Cross-model fact-check of summaries (Codex checks what Claude wrote).
Scope: ALL suspect-tier papers + corrected/updated summaries (v>=2 not yet
re-checked) + a random sample of the rest (default 10%). Codex gets the summary +
the paper PDF dropped into an isolated sandbox and reads it ITSELF (extracts text
for numbers, renders pages for formulas/figures) — no pre-extracted text fed in.
Verifies numbers/claims, reports issues. REPORT ONLY — never modifies summaries
(corrections are correct_summaries.py's job).
State: topics/<id>/verified.json maps paper_id -> last verified summary version,
so re-runs sample fresh papers and corrected versions become eligible again.
For auto-escalating rounds / full sweeps use escalate_verify.py.
Usage: python3 pipeline/stages/verify_summaries.py <topicId> [samplePct] [concurrency] [--limit N]
"""
import json
import random
import shutil
import tempfile
import sys
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT, now_iso, load_config
from lib.codex import run_codex, pool
from lib.log import get_logger, run_log
from summarize_auto import full_text

MAX_CHARS = 400000
log = get_logger("verify")

# B 选项(默认):纯把 PDF 扔给 Codex——给它隔离临时目录(拷入 paper.pdf)+ workspace-write 沙箱,
# 它自己读全篇:命令行抽文本查数字 + 涉及公式/图/表时自渲染相关页面成图片再看
# (实测 gpt-5.5 会用 PIL/pdftoppm 渲染甚至裁剪放大)。prompt 里不预喂抽取文本。
# 关掉=调试/省钱模式:不开沙箱,把这份 PDF 的 pdftotext 文本喂进 prompt(同源,但公式/图表里的错查不出)。
# 两种模式都以 PDF 为唯一原文来源;PDF 不在盘上 = 异常,记错误跳过(不退回 text_path 偷换来源)。
USE_SELF_RENDER = (load_config().get("verify") or {}).get("codex_self_render", True)


def vprompt(title, summary, text=None, truncated=False, pdf_mode=False):
    if pdf_mode:
        # B:原文只以 PDF 形式给 Codex,prompt 里不放抽取文本,让它自己读全篇。
        intro = "下面是一篇论文的中文总结,论文原文以 PDF 形式放在当前目录(./paper.pdf)。"
        source_directive = ("\n- 当前目录下有这篇论文的 PDF: **./paper.pdf**,这是唯一的原文来源。"
                            "**请你自己读取它来核查**:用命令行(如 pdftotext)抽出全文核对数字与论断,"
                            "务必读完整篇、不要只看前几页;凡涉及公式/图/表的数据,把相关页面渲染成图片"
                            "(放当前目录)再看,以页面图像为准,不要凭可能损坏的抽取文本就判总结有错。")
        trunc_note = ""
        source_block = "==== 论文原文 ====\n见当前目录的 ./paper.pdf(按上面要求自行读取)"
    else:
        # 兜底:PDF 不在盘上(或开关关闭),退回把抽取文本直接喂进 prompt。
        intro = "下面是一篇论文的中文总结和论文原文(纯文本)。"
        source_directive = ""
        trunc_note = ("\n- ⚠️ 提供的原文在末尾被截断([原文已截断]标记)。对于给定原文中找不到、"
                      "但可能位于截断部分的内容(如长综述后部的应用案例/附录数据),"
                      "**不要计为问题**——核不到≠编造。只报告与给定原文**明确矛盾**的内容。"
                      if truncated else "")
        source_block = f"==== 论文原文 ====\n{text}"
    return f"""你是独立的事实核查员(与撰写总结的模型不同,专查它的幻觉)。{intro}

你的唯一任务:核对总结中的**数字和关键论断**是否有原文依据。逐条检查:
- 总结里的每个具体数字(指标、样本量、提升幅度)在原文中是否存在且未被歪曲
- 总结归给作者的每个关键论断,原文是否真的这么说(注意"作者声称X"被写成"X成立"的偷换)
- 是否有原文完全没有的内容被编进总结
不要评价总结的文笔/完整性/选材,只查"有没有依据"。{source_directive}
例外(跳过不查):
- 总结标题下方以 "> " 开头的元信息行(作者/年份/venue/引用数/DOI)来自我们的文献数据库,不是从论文里抄的;YAML 头(--- 包围)同理。
- "局限与我的质疑"一节中**总结者自己的批判与评注**(对论文领域地位/历史影响的判断、与我们研究主题契合度的评价、对后续工作的展望、标注"(总结者注)"的内容)——这些本来就不是论文论断,不需要原文依据。但该节中**转述作者自述局限**的部分仍要核。{trunc_note}

**只输出一个 JSON 对象**,不要解释、不要代码围栏,格式:
{{"verdict":"pass|minor|major","issues":[{{"quote":"<总结中有问题的原句,截取关键部分>","problem":"<问题是什么,一句话中文>","severity":"minor|major"}}]}}
- pass = 抽不出实质问题;minor = 小偏差(数字略有出入/表述过强);major = 编造或严重歪曲。
- 没有问题就输出 {{"verdict":"pass","issues":[]}}。

==== 论文标题 ====
{title}

==== 中文总结 ====
{summary}

{source_block}"""


def parse_obj(out):
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j < i:
        raise ValueError("no JSON object in output")
    return json.loads(out[i:j + 1])


def _seen_path(topic_id):
    return ROOT / "topics" / topic_id / "verified.json"


def load_candidates(topic_id):
    """Latest-version summarized papers of the topic + verified-versions map."""
    conn = open_db()
    rows = [dict(r) for r in conn.execute(
        """SELECT p.*, sv.path AS summary_path, sv.version AS summary_version FROM papers p
            JOIN paper_topic pt ON pt.paper_id=p.id
            JOIN summary_versions sv ON sv.paper_id=p.id
           WHERE pt.topic_id=? AND p.status='summarized'
             AND sv.version=(SELECT MAX(version) FROM summary_versions WHERE paper_id=p.id)
           ORDER BY pt.rank""", (topic_id,)).fetchall()]
    conn.close()
    sp = _seen_path(topic_id)
    seen = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    return rows, seen


def split_must(rows, seen):
    """must = suspects + corrected/updated (v>=2) not verified at current version;
    rest = the other not-yet-verified papers (sampling pool)."""
    def is_must(r):
        return r.get("quality_tier") == "suspect" or r["summary_version"] > 1
    unseen = [r for r in rows if seen.get(r["id"]) != r["summary_version"]]
    return [r for r in unseen if is_must(r)], [r for r in unseen if not is_must(r)]


def verify_batch(picked, concurrency):
    """Codex-check each picked paper. Returns (ok_results, failed).
    Circuit breaker: once a codex usage-limit error is seen, remaining papers
    are skipped immediately instead of burning one failed call each."""
    tripped = []

    def worker(r, _i):
        if tripped:
            return {"id": r["id"], "error": "skipped (codex usage limit hit earlier in batch)"}
        spath = ROOT / r["summary_path"]
        if not spath.exists():
            return {"id": r["id"], "error": "summary file missing"}
        w = {"id": r["id"], "pdf_path": str(ROOT / r["pdf_path"]) if r.get("pdf_path") else None}
        summary = spath.read_text(encoding="utf-8")
        # summarized 的篇必然曾有 PDF(sum 阶段无 PDF 直接跳过、不产出总结)。这里没 PDF =
        # 异常(被删/移动)→ 记错误跳过、进报告"未能核查"让人看,绝不退回 text_path 等别的来源
        # 去核一份本就从 PDF 写出来的总结(那正是我们要摆脱的偷换来源)。
        if not (w["pdf_path"] and Path(w["pdf_path"]).exists()):
            return {"id": r["id"], "error": "no pdf on disk (anomaly: summarized paper lost its PDF)"}
        tmpd, sandbox, cwd = None, None, None
        if USE_SELF_RENDER:
            # B:纯把 PDF 扔给 Codex——隔离临时目录(拷入 paper.pdf)+ workspace-write,
            # 让它自己读全篇(抽文本查数字 + 按需渲染页面看公式/图表),不预喂抽取文本。
            tmpd = Path(tempfile.mkdtemp(prefix="vfy_cdx_"))
            shutil.copy2(w["pdf_path"], tmpd / "paper.pdf")
            sandbox, cwd = "workspace-write", str(tmpd)
            prompt, timeout = vprompt(r["title"], summary, pdf_mode=True), 900
        else:
            # 调试/省钱:不开沙箱,把这份 PDF 的 pdftotext 文本喂进 prompt(同源,但看不到公式/图表)。
            text = full_text(w, prefer_pdf=True)
            if not text:
                return {"id": r["id"], "error": "pdf on disk but text extraction failed"}
            truncated = len(text) > MAX_CHARS
            sent = text[:MAX_CHARS] + ("\n\n[原文已截断:超出长度上限,以上仅为前一部分]" if truncated else "")
            prompt, timeout = vprompt(r["title"], summary, sent, truncated, pdf_mode=False), 600
        try:
            out = run_codex(prompt, sandbox=sandbox, cwd=cwd, timeout=timeout)
        except Exception as e:
            if "usage limit" in str(e).lower():
                tripped.append(True)
            raise
        finally:
            if tmpd:
                shutil.rmtree(tmpd, ignore_errors=True)
        v = parse_obj(out)
        res = {"id": r["id"], "title": r["title"], "tier": r.get("quality_tier"),
               "version": r["summary_version"],
               "verdict": v.get("verdict", "?"), "issues": v.get("issues") or []}
        log.info(f"  {res['verdict'].upper():5s} ({len(res['issues'])} issues) {r['title'][:60]}")
        return res

    results = pool(picked, worker, concurrency)
    ok = [r for r in results if isinstance(r, dict) and r.get("verdict")]
    failed = [r for r in results if not (isinstance(r, dict) and r.get("verdict"))]
    return ok, failed


def record_verified(topic_id, ok):
    sp = _seen_path(topic_id)
    seen = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    for r in ok:
        seen[r["id"]] = r["version"]
    sp.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")


def write_report(topic_id, ok, failed, note=""):
    n_pass = sum(1 for r in ok if r["verdict"] == "pass")
    n_minor = sum(1 for r in ok if r["verdict"] == "minor")
    n_major = sum(1 for r in ok if r["verdict"] == "major")
    lines = [f"# Summary verification — {topic_id}",
             f"_generated: {now_iso()}  checked: {len(ok)}/{len(ok) + len(failed)}  "
             f"pass: {n_pass}  minor: {n_minor}  major: {n_major}  errors: {len(failed)}_",
             "", "核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。"]
    if note:
        lines.append(note)
    lines.append("")
    for r in ok:
        if r["verdict"] == "pass":
            continue
        lines.append(f"## {'🔴' if r['verdict'] == 'major' else '🟠'} [{r['verdict']}] {r['title'][:90]}")
        lines.append(f"`{r['id']}` v{r['version']}" + (f"  (quality: {r['tier']})" if r.get("tier") else ""))
        for i in r["issues"]:
            lines.append(f"- **[{i.get('severity', '?')}]** “{i.get('quote', '')[:120]}” — {i.get('problem', '')}")
        lines.append("")
    if n_pass:
        lines.append(f"## ✅ pass ({n_pass})")
        lines += [f"- {r['title'][:90]} (v{r['version']})" for r in ok if r["verdict"] == "pass"]
    if failed:
        lines.append(f"\n## ⚙️ 未能核查 ({len(failed)})")
        lines += [f"- {json.dumps(r, ensure_ascii=False, default=str)[:150]}" for r in failed]

    report = ROOT / "topics" / topic_id / "summary_verification.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"  -> {report.relative_to(ROOT)}")
    return n_pass, n_minor, n_major


def main():
    if len(sys.argv) < 2:
        print("usage: verify_summaries.py <topicId> [samplePct] [concurrency] [--limit N]", file=sys.stderr)
        sys.exit(1)
    args = [a for a in sys.argv[1:] if a != "--limit"]
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
        args = [a for a in args if a != str(limit)]
    topic_id = args[0]
    pct = float(args[1]) if len(args) > 1 else 10.0
    concurrency = int(args[2]) if len(args) > 2 else 2

    rows, seen = load_candidates(topic_id)
    must, rest = split_must(rows, seen)
    n_sample = max(1, round(len(rest) * pct / 100)) if rest else 0
    picked = must + random.sample(rest, min(n_sample, len(rest)))
    if limit:
        picked = picked[:limit]
    log.info(f"verify_summaries: {len(rows)} summarized, {len(seen)} already verified, "
             f"checking {len(picked)} (must[suspect/v2+]={len(must)}, sample {pct:.0f}%={n_sample}"
             f"{f', capped to {limit}' if limit else ''})")

    ok, failed = verify_batch(picked, concurrency)
    n_pass, n_minor, n_major = write_report(topic_id, ok, failed)
    record_verified(topic_id, ok)
    run_log(topic_id, f"verify_summaries: checked={len(ok)} pass={n_pass} minor={n_minor} "
                      f"major={n_major} errors={len(failed)}")


if __name__ == "__main__":
    main()
