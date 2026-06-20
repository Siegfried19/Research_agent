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

Two modes:
- capped (run.py's `verify` stage, pass --max-papers): NO sampling/escalation —
  all unverified summaries are eligible, newest-summarized first, and --max-papers
  decides how many get checked this run; later rounds only re-check redone versions.
  --start-pct is ignored here. This is the nightly/auto path: it keeps verify inside
  one codex quota window so new summaries enter the library already fact-checked.
- sampling (manual/debug, no --max-papers): check --start-pct% of the pool; if the
  fresh-sample major rate >= threshold, DOUBLE the sample next round (what "escalate"
  refers to). pct/threshold matter only here.

Per-paper redo attempts are capped (default 2 per run); a paper still major
after that is flagged in the report for human triage, not looped forever.
Verification is advisory: exit code is 0 even if issues remain (see report).
--max-papers N caps the total papers checked this run (incl. major re-checks) so
it stays inside one codex quota window (~20 for this subscription); leftover is
reported and drained on the next run, newest-summarized first.
Usage: python3 pipeline/verify/escalate_verify.py <topicId> [--start-pct P] [--threshold T]
       [--concurrency N] [--max-rounds R] [--max-attempts A] [--max-papers M]
"""
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.log import get_logger, run_log
from lib.notify import notify
from verify_summaries import (load_candidates, split_must, verify_batch,
                              record_verified, record_verify_detail, write_report,
                              classify_and_signal, record_skip)
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
    pct = flag(argv, "--start-pct", 100.0)  # 仅 sampling 模式(不传 --max-papers)有意义;capped 模式忽略
    threshold = flag(argv, "--threshold", 10.0)          # fresh-sample major %, escalate at/above
    concurrency = flag(argv, "--concurrency", 3, int)
    max_rounds = flag(argv, "--max-rounds", 6, int)
    max_attempts = flag(argv, "--max-attempts", 2, int)  # corrections per paper per run
    # 全程总量上限(含 major 复核):主动停在 codex 配额窗口以内(此订阅 ~20 次/窗口,
    # 见 logs/SESSION-2026-06-17-codex-quota.md)。None=不限(手动全量核查时用)。
    max_papers = int(argv[argv.index("--max-papers") + 1]) if "--max-papers" in argv else None
    # 两模式(2026-06-19 拆清,治"--start-pct 100 + 上限"的冗余):
    #   capped —— run auto 走这条(传 --max-papers):不抽样/不翻倍,所有未核都合格、最近总结的优先,
    #     由 --max-papers 定本轮核几篇;跨轮只为复核重做出的新版。--start-pct 在此模式被忽略。
    #   sampling —— 手动调试用(不传 --max-papers):抽 --start-pct%,fresh major 率≥阈值则下轮翻倍
    #     扩面(escalate 本名由来)。pct/threshold 仅此模式有意义。
    capped_mode = max_papers is not None

    attempts = {}        # paper_id -> corrections made this run
    all_results = {}     # paper_id -> latest result (across rounds)
    all_failed = []
    stubborn = set()     # still major after max_attempts
    pending_recheck = False
    quota_stopped = False  # 因 codex 侧问题(配额/瞬时/真故障)中止(已发 Telegram)
    stop_cat = None        # 中止时的失败类别(LLM 判,见 lib/error_classify)
    capped = False         # 达到 --max-papers 上限而停(剩余留下次)
    budget = max_papers    # 剩余可核次数(None=不限);每轮按 len(picked) 递减

    for rnd in range(1, max_rounds + 1):
        if budget is not None and budget <= 0:
            capped = True
            log.info(f"escalate r{rnd}: 达到 --max-papers={max_papers} 上限,停(剩余留下次/下窗口)")
            break
        rows, seen, skip = load_candidates(topic_id)
        must, rest = split_must(rows, seen, skip)
        # 篇序:最近总结的排最前(夜间先核当晚那批,旧积压留后)——取代随机抽样,配合上限确定性。
        rest.sort(key=lambda r: r.get("summary_created") or "", reverse=True)
        if capped_mode:
            fresh = rest                 # 全部未核都合格;实际核几篇由下面 budget 上限截断
        else:
            n_sample = min(len(rest), max(1, round(len(rest) * pct / 100))) if rest else 0
            fresh = rest[:n_sample]
        picked = must + fresh
        if budget is not None:
            picked = picked[:budget]   # 总量封顶(must 优先);超出的留到下次/额度恢复
        if not picked:
            log.info(f"escalate r{rnd}: nothing left to verify — done")
            break
        picked_ids = {r["id"] for r in picked}
        fresh_ids = {r["id"] for r in fresh if r["id"] in picked_ids}
        if budget is not None:
            budget -= len(picked)
        log.info(f"escalate r{rnd}: checking {len(picked)} (must={len(must)}, "
                 f"fresh[{'capped' if capped_mode else f'{pct:.0f}%'}]={len(fresh_ids)}, "
                 f"unverified left={len(must) + len(rest)}"
                 f"{f', budget left {budget}' if budget is not None else ''})")

        ok, failed = verify_batch(picked, concurrency)
        record_verified(topic_id, ok)
        record_verify_detail(ok)   # 详情按版本留痕(同 verify_summaries)
        for r in ok:
            all_results[r["id"]] = r
        all_failed += failed
        # 失败统一交 LLM 分类(不再靠关键词,见 lib/error_classify):
        #   quota/transient/unknown/real_error → 写信号给 daemon + 中止本轮(daemon 按类睡:配额长睡/
        #     瞬时递增退避/真故障跳主题);bad_input/malformed → 那几篇钉版跳过,不中止整轮。
        if failed:
            d = classify_and_signal(topic_id, failed)
            if d["skip_papers"]:
                record_skip(topic_id, d["skip_papers"], f"verify 判为 {d['category']}")
                log.info(f"escalate r{rnd}: {len(d['skip_papers'])} 篇判 {d['category']} -> 钉版跳过(record_skip)")
            if d["stop"]:
                quota_stopped, stop_cat = True, d["category"]
                pending = max(0, len(must) + len(rest) - len(ok))
                log.info(f"escalate r{rnd}: 失败类别={d['category']} -> 写信号 + 中止"
                         f"(本轮已核 {len(ok)},累计 {len(all_results)},约 {pending} 篇待核"
                         f"{f',约 {d['until']} 重试' if d['until'] else ''})")
                notify(f"⚠️ verify 中止（{d['category']}，topic {topic_id}）。"
                       f"本轮已核 {len(ok)}、累计 {len(all_results)}，约 {pending} 篇待核。"
                       + (f"约 {d['until'][11:16]} 后重试。" if d['until'] else "")
                       + "重跑即从断点续核（verified.json 已落盘）。")
                break
        if not ok:
            # 没触发 stop(非 codex 侧问题)但本轮一篇没核成 → 失败多被判 bad_input/malformed 钉版跳过了,
            # 没有可推进的了 → 收尾退出(不再像旧版那样误判成"坏PDF整主题需人工")。
            log.info(f"escalate r{rnd}: 本轮 0 篇核成(失败均已分类/钉版处理)— 结束")
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

        # 抽样翻倍仅 sampling 模式有意义;capped(run auto)只靠 --max-papers 上限限流,不翻倍。
        if not capped_mode and fresh_ok and fresh_major_pct >= threshold:
            pct = min(100.0, pct * 2)
            log.info(f"escalate r{rnd}: rate over threshold -> escalating sample to {pct:.0f}%")
        elif not pending_recheck:
            log.info(f"escalate r{rnd}: nothing left to re-check — done")
            break

    results = list(all_results.values())
    for r in results:
        if r["id"] in stubborn:
            r["issues"] = (r.get("issues") or []) + [{
                "severity": "major",
                "quote": "(escalate_verify)",
                "problem": f"重做 {max_attempts} 次后复核仍 major,需人工分诊"}]
    # 剩余未核:本主题已总结但还没核到当前版本的篇数(报告 + Telegram + 日志都报,治"积压看不见")。
    rows_after, seen_after, skip_after = load_candidates(topic_id)
    must_after, rest_after = split_must(rows_after, seen_after, skip_after)
    remaining = len(must_after) + len(rest_after)
    cap_note = (f"🧮 **本轮达 --max-papers={max_papers} 上限而停**,剩 {remaining} 篇待核——"
                f"再跑 verify 即从断点续核(篇序:最近总结的优先)。\n" if capped else "")
    quota_note = (f"⚠️ **本轮因 codex 侧问题（{stop_cat}）中止**,部分篇未核(已发 Telegram)——"
                  "待恢复后重跑 verify 即从断点续核。\n" if quota_stopped else "")
    n_pass, n_minor, n_major = write_report(
        topic_id, results, all_failed,
        note=(quota_note + cap_note
              + f"本主题尚有 **{remaining}** 篇待核查。"
              + f"本报告由 escalate_verify 汇总(多轮升级抽检,major 自动整篇重新总结+复核;"
                f"标注\"需人工分诊\"的为重做 {max_attempts} 次仍 major)。"))
    log.info(f"escalate done: {len(results)} papers verified this run, "
             f"pass={n_pass} minor={n_minor} major={n_major}, "
             f"redone={sum(attempts.values())}, stubborn={len(stubborn)}, "
             f"剩余待核={remaining}{' [达上限]' if capped else ''}{' [配额中止]' if quota_stopped else ''}")
    run_log(topic_id, f"escalate_verify: verified={len(results)} pass={n_pass} minor={n_minor} "
                      f"major={n_major} redone={sum(attempts.values())} "
                      f"stubborn={len(stubborn)} errors={len(all_failed)} remaining={remaining}"
                      f"{' capped' if capped else ''}{' quota-stop' if quota_stopped else ''}")


if __name__ == "__main__":
    main()
