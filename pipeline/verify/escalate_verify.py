"""Auto-escalating verification driver (固化"命中就扩面"升级阶梯).
Round loop: verify (default 100% = all unverified) → for every MAJOR, redo the
whole summary from the PDF (summarize_auto.resummarize — a fresh re-summary, not
a patch; the issue list is fed only as "avoid these pitfalls", no authority to
reverse-judge the source). minor (isolated number precision / slightly-strong
wording) and unverifiable (not checked this round) are REPORT-ONLY — not redone.
If the fresh-sample major rate >= threshold also DOUBLE the sample → repeat.
Redone versions are re-verified next round.
Stops when: fresh major rate below threshold AND nothing pending re-check, or
every paper is verified, or max-rounds is hit.

--start-pct 100 = full-sweep mode: check ALL unverified summaries, redo majors,
re-check once. This is what run.py's `verify` stage uses after `sum`, so new
summaries enter the library already fact-checked.

Per-paper redo attempts are capped (default 2 per run); a paper still major
after that is flagged in the report for human triage, not looped forever.
Verification is advisory: exit code is 0 even if issues remain (see report).
Usage: python3 pipeline/verify/escalate_verify.py <topicId> [--start-pct P] [--threshold T]
       [--concurrency N] [--max-rounds R] [--max-attempts A]
"""
import random
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.log import get_logger, run_log
from verify_summaries import load_candidates, split_must, verify_batch, record_verified, write_report
from summarize.summarize_auto import resummarize  # 跨段 import:重做=从 PDF 整篇重新总结

log = get_logger("escalate")


def flag(argv, name, default, cast=float):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    argv = sys.argv[1:]
    topic_id = argv[0]
    pct = flag(argv, "--start-pct", 100.0)  # 默认全审(每次就 ~10 篇,不抽样)
    threshold = flag(argv, "--threshold", 10.0)          # fresh-sample major %, escalate at/above
    concurrency = flag(argv, "--concurrency", 3, int)
    max_rounds = flag(argv, "--max-rounds", 6, int)
    max_attempts = flag(argv, "--max-attempts", 2, int)  # corrections per paper per run

    attempts = {}        # paper_id -> corrections made this run
    all_results = {}     # paper_id -> latest result (across rounds)
    all_failed = []
    stubborn = set()     # still major after max_attempts
    pending_recheck = False

    for rnd in range(1, max_rounds + 1):
        rows, seen = load_candidates(topic_id)
        must, rest = split_must(rows, seen)
        n_sample = min(len(rest), max(1, round(len(rest) * pct / 100))) if rest else 0
        fresh = random.sample(rest, n_sample)
        picked = must + fresh
        if not picked:
            log.info(f"escalate r{rnd}: nothing left to verify — done")
            break
        fresh_ids = {r["id"] for r in fresh}
        log.info(f"escalate r{rnd}: checking {len(picked)} (must={len(must)}, "
                 f"fresh {pct:.0f}%={len(fresh)}, unverified left={len(must) + len(rest)})")

        ok, failed = verify_batch(picked, concurrency)
        record_verified(topic_id, ok)
        for r in ok:
            all_results[r["id"]] = r
        all_failed += failed
        if not ok:
            log.info(f"escalate r{rnd}: all {len(failed)} checks failed (codex down/rate-limited?) — aborting")
            break

        majors = [r for r in ok if r["verdict"] == "major"]
        # 只有 major 触发重做(2026-06-18 定稿):major=会污染"值不值得深入"判断的错
        # (方向反转/张冠李戴/过度声称/编造原文没有的事实)。minor(孤立数字精度/措辞略强)与
        # unverifiable(这轮没核到、非错误)只进报告、不重做——精度让位 PDF,没核到重做也没用。
        # 重做=从 PDF **整篇重新总结**(resummarize,无裁决权),不是在旧版上打补丁。两次仍 major 转人工。
        fixable = [m for m in majors if attempts.get(m["id"], 0) < max_attempts]
        stubborn |= {m["id"] for m in majors if attempts.get(m["id"], 0) >= max_attempts}
        fresh_ok = [r for r in ok if r["id"] in fresh_ids]
        fresh_major_pct = (100.0 * sum(1 for r in fresh_ok if r["verdict"] == "major")
                           / len(fresh_ok)) if fresh_ok else 0.0
        log.info(f"escalate r{rnd}: pass={sum(1 for r in ok if r['verdict'] == 'pass')} "
                 f"minor={sum(1 for r in ok if r['verdict'] == 'minor')} major={len(majors)} "
                 f"unverifiable={sum(1 for r in ok if r['verdict'] == 'unverifiable')} "
                 f"| fresh major rate {fresh_major_pct:.0f}% (threshold {threshold:.0f}%)")

        pending_recheck = False
        if fixable:
            for m in fixable:
                attempts[m["id"]] = attempts.get(m["id"], 0) + 1
            done = resummarize([{"paperId": m["id"], "issues": m["issues"]} for m in fixable],
                               concurrency, topic_id=topic_id)
            pending_recheck = bool(done)

        if fresh_ok and fresh_major_pct >= threshold:
            pct = min(100.0, pct * 2)
            log.info(f"escalate r{rnd}: rate over threshold -> escalating sample to {pct:.0f}%")
        elif not pending_recheck:
            log.info(f"escalate r{rnd}: rate under threshold, nothing to re-check — done")
            break

    results = list(all_results.values())
    for r in results:
        if r["id"] in stubborn:
            r["issues"] = (r.get("issues") or []) + [{
                "severity": "major",
                "quote": "(escalate_verify)",
                "problem": f"重做 {max_attempts} 次后复核仍 major,需人工分诊"}]
    n_pass, n_minor, n_major = write_report(
        topic_id, results, all_failed,
        note=f"本报告由 escalate_verify 汇总(多轮升级抽检,major 自动整篇重新总结+复核;"
             f"标注\"需人工分诊\"的为重做 {max_attempts} 次仍 major)。")
    log.info(f"escalate done: {len(results)} papers verified this run, "
             f"pass={n_pass} minor={n_minor} major={n_major}, "
             f"redone={sum(attempts.values())}, stubborn={len(stubborn)}")
    run_log(topic_id, f"escalate_verify: verified={len(results)} pass={n_pass} minor={n_minor} "
                      f"major={n_major} redone={sum(attempts.values())} "
                      f"stubborn={len(stubborn)} errors={len(all_failed)}")


if __name__ == "__main__":
    main()
