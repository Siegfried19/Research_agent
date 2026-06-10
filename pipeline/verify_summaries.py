"""Cross-model fact-check of summaries (Codex checks what Claude wrote).
Scope: ALL suspect-tier papers + a random sample of the rest (default 10%).
Codex reads summary + full text, verifies numbers/claims, reports issues.
REPORT ONLY — never modifies summaries. -> topics/<id>/summary_verification.md
Usage: python3 pipeline/verify_summaries.py <topicId> [samplePct] [concurrency] [--limit N]
"""
import json
import random
import sys
from pathlib import Path

from lib.db import open_db, ROOT, now_iso
from lib.codex import run_codex, pool
from lib.log import get_logger, run_log
from summarize_auto import full_text

MAX_CHARS = 100000
log = get_logger("verify")


def vprompt(title, summary, text):
    return f"""你是独立的事实核查员(与撰写总结的模型不同,专查它的幻觉)。下面是一篇论文的中文总结和论文原文。

你的唯一任务:核对总结中的**数字和关键论断**是否有原文依据。逐条检查:
- 总结里的每个具体数字(指标、样本量、提升幅度)在原文中是否存在且未被歪曲
- 总结归给作者的每个关键论断,原文是否真的这么说(注意"作者声称X"被写成"X成立"的偷换)
- 是否有原文完全没有的内容被编进总结
不要评价总结的文笔/完整性/选材,只查"有没有依据"。
例外:总结标题下方以 "> " 开头的元信息行(作者/年份/venue/引用数/DOI)来自我们的文献数据库,不是从论文里抄的,**跳过不查**;YAML 头(--- 包围)同理跳过。

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

    conn = open_db()
    rows = [dict(r) for r in conn.execute(
        """SELECT p.*, sv.path AS summary_path FROM papers p
            JOIN paper_topic pt ON pt.paper_id=p.id
            JOIN summary_versions sv ON sv.paper_id=p.id
           WHERE pt.topic_id=? AND p.status='summarized'
             AND sv.version=(SELECT MAX(version) FROM summary_versions WHERE paper_id=p.id)
           ORDER BY pt.rank""", (topic_id,)).fetchall()]
    conn.close()

    must = [r for r in rows if r.get("quality_tier") == "suspect"]
    rest = [r for r in rows if r.get("quality_tier") != "suspect"]
    n_sample = max(1, round(len(rest) * pct / 100)) if rest else 0
    picked = must + random.sample(rest, min(n_sample, len(rest)))
    if limit:
        picked = picked[:limit]
    log.info(f"verify_summaries: {len(rows)} summarized, checking {len(picked)} "
             f"(suspect={len(must)}, sample {pct:.0f}%={n_sample}{f', capped to {limit}' if limit else ''})")

    def worker(r, _i):
        spath = ROOT / r["summary_path"]
        if not spath.exists():
            return {"id": r["id"], "error": "summary file missing"}
        w = {"id": r["id"], "text_path": str(ROOT / r["text_path"]) if r.get("text_path") else None,
             "pdf_path": str(ROOT / r["pdf_path"]) if r.get("pdf_path") else None}
        text = full_text(w)
        if not text:
            return {"id": r["id"], "error": "no fulltext"}
        v = parse_obj(run_codex(vprompt(r["title"], spath.read_text(encoding="utf-8"),
                                        text[:MAX_CHARS]), timeout=600))
        res = {"id": r["id"], "title": r["title"], "tier": r.get("quality_tier"),
               "verdict": v.get("verdict", "?"), "issues": v.get("issues") or []}
        log.info(f"  {res['verdict'].upper():5s} ({len(res['issues'])} issues) {r['title'][:60]}")
        return res

    results = pool(picked, worker, concurrency)
    ok = [r for r in results if isinstance(r, dict) and r.get("verdict")]
    failed = [r for r in results if not (isinstance(r, dict) and r.get("verdict"))]
    n_pass = sum(1 for r in ok if r["verdict"] == "pass")
    n_minor = sum(1 for r in ok if r["verdict"] == "minor")
    n_major = sum(1 for r in ok if r["verdict"] == "major")

    lines = [f"# Summary verification — {topic_id}",
             f"_generated: {now_iso()}  checked: {len(ok)}/{len(picked)}  "
             f"pass: {n_pass}  minor: {n_minor}  major: {n_major}  errors: {len(failed)}_",
             "", "核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。", ""]
    for r in ok:
        if r["verdict"] == "pass":
            continue
        lines.append(f"## {'🔴' if r['verdict'] == 'major' else '🟠'} [{r['verdict']}] {r['title'][:90]}")
        lines.append(f"`{r['id']}`" + (f"  (quality: {r['tier']})" if r.get("tier") else ""))
        for i in r["issues"]:
            lines.append(f"- **[{i.get('severity', '?')}]** “{i.get('quote', '')[:120]}” — {i.get('problem', '')}")
        lines.append("")
    if n_pass:
        lines.append(f"## ✅ pass ({n_pass})")
        lines += [f"- {r['title'][:90]}" for r in ok if r["verdict"] == "pass"]
    if failed:
        lines.append(f"\n## ⚙️ 未能核查 ({len(failed)})")
        lines += [f"- {json.dumps(r, ensure_ascii=False)[:150]}" for r in failed]

    report = ROOT / "topics" / topic_id / "summary_verification.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"  -> {report.relative_to(ROOT)}")
    run_log(topic_id, f"verify_summaries: checked={len(ok)} pass={n_pass} minor={n_minor} "
                      f"major={n_major} errors={len(failed)}")


if __name__ == "__main__":
    main()
