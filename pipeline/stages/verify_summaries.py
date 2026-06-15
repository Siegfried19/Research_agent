"""Cross-model fact-check of summaries (Codex checks what Claude wrote).
Scope: ALL suspect-tier papers + corrected/updated summaries (v>=2 not yet
re-checked) + a random sample of the rest (default 10%). Codex reads summary +
full text, verifies numbers/claims, reports issues. REPORT ONLY — never modifies
summaries (corrections are correct_summaries.py's job).
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

# 让 Codex 自己渲染 PDF:给它一个临时工作目录(拷入 paper.pdf)+ workspace-write 沙箱,
# 涉及公式/图/表时它会自己把相关页面渲成图片再看(实测 gpt-5.5 会用 PIL/pdftoppm 渲染甚至裁剪放大)。
# 关掉=纯文本核查(只喂 pdftotext 文本,公式/图表里的错查不出)。
USE_SELF_RENDER = (load_config().get("verify") or {}).get("codex_self_render", True)


def vprompt(title, summary, text, truncated=False, self_render=False):
    trunc_note = ("\n- ⚠️ 提供的原文在末尾被截断([原文已截断]标记)。对于给定原文中找不到、"
                  "但可能位于截断部分的内容(如长综述后部的应用案例/附录数据),"
                  "**不要计为问题**——核不到≠编造。只报告与给定原文**明确矛盾**的内容。"
                  if truncated else "")
    render_note = ("\n- 当前目录下有这篇论文的 PDF: **./paper.pdf**。纯文本抽取常把公式、图、表格弄乱或丢失,"
                   "凡涉及公式/图表数据的核对,**请自己把相关页面渲染成图片(把图片放在当前目录)再看**,以页面图像为准,"
                   "不要仅凭可能损坏的文本就判定总结有错。" if self_render else "")
    return f"""你是独立的事实核查员(与撰写总结的模型不同,专查它的幻觉)。下面是一篇论文的中文总结和论文原文(纯文本){"，论文 PDF 也在当前目录可供你自行渲染查看" if self_render else ""}。

你的唯一任务:核对总结中的**数字和关键论断**是否有原文依据。逐条检查:
- 总结里的每个具体数字(指标、样本量、提升幅度)在原文中是否存在且未被歪曲
- 总结归给作者的每个关键论断,原文是否真的这么说(注意"作者声称X"被写成"X成立"的偷换)
- 是否有原文完全没有的内容被编进总结
不要评价总结的文笔/完整性/选材,只查"有没有依据"。{render_note}
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

==== 论文原文 ====
{text}"""


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
        w = {"id": r["id"], "text_path": str(ROOT / r["text_path"]) if r.get("text_path") else None,
             "pdf_path": str(ROOT / r["pdf_path"]) if r.get("pdf_path") else None}
        # prefer_pdf:核查者直接读 PDF 抽的文本,跟撰写者(sum 直读 PDF)读同一份源,
        # 避免拿到一份不同来源/可能过时的 text_path。文本管全量查数字。
        text = full_text(w, prefer_pdf=True)
        if not text:
            return {"id": r["id"], "error": "no fulltext"}
        truncated = len(text) > MAX_CHARS
        sent = text[:MAX_CHARS] + ("\n\n[原文已截断:超出长度上限,以上仅为前一部分]" if truncated else "")
        # 自渲染模式:给 Codex 一个隔离的临时工作目录(拷入 paper.pdf)+ workspace-write,
        # 涉及公式/图表它会自己渲染相关页面再看。scratch 全在 tmpd 里,finally 清掉。
        tmpd, sandbox, cwd = None, None, None
        self_render = USE_SELF_RENDER and w["pdf_path"] and Path(w["pdf_path"]).exists()
        if self_render:
            tmpd = Path(tempfile.mkdtemp(prefix="vfy_cdx_"))
            shutil.copy2(w["pdf_path"], tmpd / "paper.pdf")
            sandbox, cwd = "workspace-write", str(tmpd)
        try:
            out = run_codex(vprompt(r["title"], spath.read_text(encoding="utf-8"),
                                    sent, truncated, self_render=bool(self_render)),
                            sandbox=sandbox, cwd=cwd, timeout=900 if self_render else 600)
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
