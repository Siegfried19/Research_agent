"""Orchestrate one run of a topic through its stages (Python).

  python3 pipeline/run.py <topicId> <stage>

Stages:
  discover  multi-source search        -> topics/<id>/candidates.json
  score     relevance scoring (claude -p) -> scores/batch_*.json
  commit    select + write DB (additive on incremental)
  fetch     download OA full text (+ arXiv fallback)
  recover   free fallback: Unpaywall + arXiv (repository-first) + DBLP/PMLR
  hunt      agentic free-source hunt (claude -p + web search) for what's left
  tierb     paywall full text via browser + NYU OpenAthens (you click challenges)
  worklist  build summarize worklist
  sum       summaries (claude -p) -> v1.md
  finalize  register summaries + render topic.md
  verify    cross-model fact-check unverified summaries (Codex, ≤VERIFY_MAX_PER_RUN
            per run, newest first), redo majors whole (claude -p, vN+1) + re-check,
            report papers still pending, then re-render topic.md
  auto      run all of the above, in order

  auto-pull  daytime/attended half: discover..hunt + tierb + worklist.
             Gets every PDF ready (incl. paywalled — you click tierb challenges).
             Token cost = score + hunt only (small).
  auto-sum   nightly/unattended half: sum + finalize (verify split out → daemon).
             The token-heavy summarize, meant to run via cron while you sleep so
             it doesn't compete with your daytime Max usage. No human, no paywall.
             Idempotent — already-summarized papers are skipped, so a partial run
             just gets finished on the next night. Fact-checking (verify) is no
             longer in this chain: it runs all-day via tools/verify_daemon.py so
             the two don't fight over the same codex quota window.

Only `tierb` ever needs you (to click a Cloudflare/Duo challenge) — and it lives
in `auto-pull`, the attended half. `auto-sum` is fully unattended.
"""
from lib.envguard import ensure_env
ensure_env()  # 不在 research-agent 环境就自动切过去(主链子进程经 sys.executable 全继承)

import json
import subprocess
import sys
from pathlib import Path

from lib.db import ROOT, open_db
from lib.log import run_log
from lib.notify import notify

PY = sys.executable
PDIR = ROOT / "pipeline"

# 每次 verify 最多核多少篇(含 major 复核):主动停在 codex 配额窗口内(此订阅 ~20 次/窗口,
# 见 logs/SESSION-2026-06-17-codex-quota.md;留 margin 给复核 → 15)。积压靠多跑几次安全排空。
# 想调就改这里(或夜间把 sum 批量降到 ~10-12 让 verify 跟得上当晚总结)。
VERIFY_MAX_PER_RUN = 15

# stage -> list of (script, [args...]) run in order
def steps(stage, tid):
    return {
        "discover": [("find/discover.py", [f"topics/{tid}/topic.json"])],
        "score":    [("find/score_auto.py", [tid])],
        "commit":   [("find/commit.py", [f"topics/{tid}"])],
        "find":     [("find/drive.py", [tid])],  # orchestrator-driven find = discover+score+commit by one Claude (default in AUTO since 2026-06-20)
        "fetch":    [("fetch/fetch_oa.py", [tid])],
        "recover":  [("fetch/recover_oa.py", [tid])],
        "hunt":     [("fetch/recover_agent.py", [tid])],
        "tierb":    [("fetch/fetch_tierb.py", [tid])],
        "worklist": [("summarize/build_worklist.py", [tid])],
        "sum":      [("summarize/summarize_auto.py", [tid])],
        "finalize": [("summarize/register_summaries.py", [tid]), ("summarize/render_topic.py", [tid])],
        "verify":   [("verify/escalate_verify.py",
                      [tid, "--max-papers", str(VERIFY_MAX_PER_RUN)]),  # capped 模式:不抽样,上限定量
                     ("summarize/render_topic.py", [tid])],
    }.get(stage)


AUTO = ["find", "fetch", "recover", "hunt", "tierb", "worklist", "sum", "finalize", "verify"]
# Token-aware split (2026-06-16): pull half is attended (tierb) + small token cost;
# sum half is the token-heavy summarize, meant for an unattended nightly cron
# (verify split out 2026-06-19 → all-day verify_daemon, so they don't share the codex window).
AUTO_PULL = ["find", "fetch", "recover", "hunt", "tierb", "worklist"]
# 2026-06-19: verify 从夜间链摘出,交给全天候 verify_daemon(tools/verify_daemon.py)单跑,
# 避免 cron 与 daemon 抢同一个 codex 配额窗口。夜间只 sum+finalize;verify 阶段保留给 daemon/手动。
AUTO_SUM = ["sum", "finalize"]


def run_chain(stages, tid, continue_on_error=False):
    """Run a list of stages in order. fail-fast by default; when
    continue_on_error, log the failure and keep going (idempotent stages), but
    still return nonzero so a cron log surfaces it."""
    final_rc = 0
    for s in stages:
        print(f"=== stage: {s} ===")
        rc = run_stage(s, tid)
        if rc != 0:
            print(f"[chain] stage {s} failed (rc={rc})", file=sys.stderr)
            if not continue_on_error:
                return rc
            final_rc = rc
    return final_rc


def run_steps(name, tid, step_list):
    """Run one named stage given an explicit (script, args) list (lets callers
    inject extra args, e.g. --limit). Mirrors run_stage's logging/fail-fast."""
    run_log(tid, f"stage:{name} start")
    rc = 0
    for script, args in step_list:
        p = subprocess.run([PY, str(PDIR / script), *args], cwd=str(ROOT))
        if p.returncode != 0:
            rc = p.returncode
            break
    run_log(tid, f"stage:{name} end(rc={rc})")
    return rc


def run_auto_sum(tid, limit=None, concurrency=2):
    """Nightly unattended half: sum -> finalize. continue-on-error (idempotent
    stages; partial progress finished next night). When limit is set, only that
    many papers are summarized this run. Fact-checking (verify) is NOT in this
    chain anymore (2026-06-19): the all-day verify_daemon owns it, so cron and
    daemon don't share the codex quota window. The burn-down report still shows
    📋待核N so you can see how much the daemon has left to check."""
    sum_args = [tid, str(concurrency)]
    if limit:
        sum_args += ["--limit", str(limit)]
    # worklist 放最前:队列模式会切主题,先重建该主题的 worklist 才自洽(便宜+幂等)。
    chain = [
        ("worklist", steps("worklist", tid)),
        ("sum",      [("summarize/summarize_auto.py", sum_args)]),
        ("finalize", steps("finalize", tid)),
        # verify 不在夜间链(2026-06-19):交给 verify_daemon 全天候啃,免与本 cron 抢 codex 配额。
        # 燃尽报告里的 📋待核N 会提示 daemon 还有多少要核。
    ]
    final_rc = 0
    for name, step_list in chain:
        print(f"=== stage: {name} ===")
        rc = run_steps(name, tid, step_list)
        if rc != 0:
            print(f"[auto-sum] stage {name} failed (rc={rc})", file=sys.stderr)
            final_rc = rc  # keep going
    return final_rc


def topic_progress(tid):
    """夜间燃尽报告用:返回该主题 (已总结, 还能做的剩余, 无PDF做不了的) 三个数。
    'doable' = status=pdf_downloaded 且 PDF 文件确实在盘上(排除永远做不了的,
    否则每晚误报"还有剩余")。让通知能分清"做完了"和"又跑了普通一晚"。"""
    conn = open_db()
    rows = conn.execute(
        """SELECT p.status AS status, p.pdf_path AS pdf_path FROM papers p
             JOIN paper_topic pt ON pt.paper_id=p.id WHERE pt.topic_id=?""", (tid,)).fetchall()
    conn.close()
    summarized = sum(1 for r in rows if r["status"] == "summarized")
    doable = stuck = 0
    for r in rows:
        if r["status"] != "pdf_downloaded":
            continue
        pp = r["pdf_path"]
        path = (Path(pp) if pp and Path(pp).is_absolute() else (ROOT / pp) if pp else None)
        if path and path.exists():
            doable += 1
        else:
            stuck += 1
    return summarized, doable, stuck


def unverified_count(tid):
    """该主题已总结但还没核到当前版本的篇数(verify 燃尽用,治"积压看不见")。"""
    conn = open_db()
    rows = conn.execute(
        """SELECT p.id AS id, MAX(sv.version) AS v FROM papers p
             JOIN paper_topic pt ON pt.paper_id=p.id
             JOIN summary_versions sv ON sv.paper_id=p.id
            WHERE pt.topic_id=? AND p.status='summarized'
            GROUP BY p.id""", (tid,)).fetchall()
    conn.close()

    def _load(name):
        p = ROOT / "topics" / tid / name
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception:
            return {}
    seen, skip = _load("verified.json"), _load("verify_skip.json")  # 钉版跳过的(坏PDF等)不算待核
    return sum(1 for r in rows
               if seen.get(r["id"]) != r["v"] and skip.get(r["id"], {}).get("version") != r["v"])


def burn_down_msg(tid, rc, limit):
    """单主题做完后的一句燃尽报告(🎉做完 / ⚠️即将耗尽 / ✅有余量) + 待核查篇数。"""
    done, doable, stuck = topic_progress(tid)
    stuck_note = f"  (另有 {stuck} 篇无PDF做不了)" if stuck else ""
    unv = unverified_count(tid)
    verify_note = f"  📋 待核查 {unv} 篇" if unv else "  ✅ 总结全部已核"
    night = limit * 2 if limit else None  # 一晚两批 -> 一晚的量
    if doable == 0:
        return (f"🎉 auto-sum done: {tid} (rc={rc}) — 该主题 {done} 篇全部已总结,无剩余"
                f"{stuck_note}{verify_note}")
    if night and doable <= night:
        return (f"⚠️ auto-sum done: {tid} (rc={rc}) — 仅剩 {doable} 篇,不足下一晚({night}),"
                f"即将耗尽,需补论文/换主题{stuck_note}{verify_note}")
    flag = "✅" if rc == 0 else "⚠️"
    return (f"{flag} auto-sum done: {tid} (rc={rc}) — 已总结 {done} 篇,剩余 {doable} 篇待做"
            f"{stuck_note}{verify_note}")


def all_topics_ordered():
    """所有主题 id,按 priority 高在前、相同则按建立序(rowid)。队列排序的唯一真相。"""
    conn = open_db()
    rows = conn.execute("SELECT id FROM topics ORDER BY priority DESC, rowid ASC").fetchall()
    conn.close()
    return [r["id"] for r in rows]


def select_next_topic():
    """挑优先级最高、且还有可做篇(doable>0)的主题;全队列做完返回 None。纯查库。"""
    for tid in all_topics_ordered():
        _, doable, _ = topic_progress(tid)
        if doable > 0:
            return tid
    return None


def queue_report():
    """全队列剩余燃尽:逐主题列出还剩多少、已做多少。"""
    lines = ["📊 全队列剩余:"]
    for tid in all_topics_ordered():
        done, doable, stuck = topic_progress(tid)
        sn = f" +{stuck}无PDF" if stuck else ""
        unv = unverified_count(tid)
        un = f" 待核{unv}" if unv else ""
        lines.append(f"   • {tid}: 剩 {doable} 篇 (已做 {done}){sn}{un}")
    return "\n".join(lines)


def refresh_index(tid="-"):
    """重建向量坐标索引(data-base/vec.sqlite),让新写/重做的总结进得了语义检索(A2,2026-06-18)。
    增量(靠 body md5,没变就跳),所以每次 summarize/verify 后跑都便宜。**best-effort**:
    无 torch/GPU(如 base 环境)时 index.py 会失败,这里吞掉不打断主链——向量本可重建、FTS
    那路每次查询自增量,缺了只是暂少语义召回那一路。"""
    run_log(tid, "reindex start")
    rc = subprocess.run([PY, str(PDIR / "retrieve" / "index.py")], cwd=str(ROOT)).returncode
    run_log(tid, f"reindex end(rc={rc})")
    if rc != 0:
        print(f"[reindex] 向量索引刷新失败(rc={rc}) — 不影响主链,可手动补: "
              f"python pipeline/retrieve/index.py", file=sys.stderr)
    return rc


def report_failed(tid):
    """⑤ 报失败:列出本主题没拿到全文的篇(跑完 fetch 链后用)。只报"是哪篇"——
    标题/id/slug/DOI/落地页,够你去手动下;失败"类型"不展示也不入库,需要时由处理的
    agent 看日志/元数据临场判。平时(全拿到)输出一行 ✅,零噪音。"""
    conn = open_db()
    rows = conn.execute(
        """SELECT p.id, p.slug, p.title, p.doi, p.landing_url, p.status, pt.rank
             FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
            WHERE pt.topic_id=? AND p.pdf_path IS NULL
              AND p.status IN ('pdf_failed','discovered')
            ORDER BY pt.rank""", (tid,)).fetchall()
    conn.close()
    if not rows:
        print(f"✅ {tid}: 全部已取到全文,无失败篇。")
        return 0
    print(f"📄 {tid}: {len(rows)} 篇没拿到全文(自己下好发我,我用 SQL 挂回库):\n")
    for r in rows:
        print(f"  [rank {r['rank']}] {(r['title'] or '')}")
        print(f"      id={r['id']}  slug={r['slug'] or '-'}  status={r['status']}")
        print(f"      DOI={r['doi'] or '-'}  落地页={r['landing_url'] or '-'}")
    return 0


def run_stage(stage, tid):
    st = steps(stage, tid)
    if st is None:
        print(f"unknown stage: {stage}", file=sys.stderr)
        return 2
    run_log(tid, f"stage:{stage} start")
    rc = 0
    for script, args in st:
        p = subprocess.run([PY, str(PDIR / script), *args], cwd=str(ROOT))
        if p.returncode != 0:
            rc = p.returncode
            break
    run_log(tid, f"stage:{stage} end(rc={rc})")
    return rc


def main():
    if len(sys.argv) < 3:
        print("usage: run.py <topicId> <stage>\n"
              "stages: discover|score|commit|fetch|recover|hunt|tierb|worklist|sum|finalize|verify|reindex|failed\n"
              "        auto (all) | auto-pull (attended half) | auto-sum [N] (nightly, single topic)\n"
              "        auto-sum-next [N] (nightly queue: picks top-priority topic with work;\n"
              "                           <topicId> ignored — reads topics table)", file=sys.stderr)
        sys.exit(1)
    tid, stage = sys.argv[1], sys.argv[2]
    if stage == "reindex":  # 手动重建向量索引(topic 无关,读全库)
        sys.exit(refresh_index(tid))
    if stage == "failed":  # ⑤ 报失败:列出没拿到全文的篇(手动下载用)
        sys.exit(report_failed(tid))
    if stage == "auto":
        rc = run_chain(AUTO, tid)
        refresh_index(tid)  # 收尾刷新语义索引(A2)
        sys.exit(rc)
    if stage == "auto-pull":
        sys.exit(run_chain(AUTO_PULL, tid))
    if stage == "auto-sum":
        # unattended nightly cron: sum -> finalize, continue-on-error (verify is
        # the all-day verify_daemon's job now, 2026-06-19 — not in this chain).
        # Optional batch size: `auto-sum <N>` caps this run to N new summaries
        # (e.g. 10) so it fits one token window; run it twice a night ~4.5h apart
        # via two cron lines to land each batch in a fresh quota window.
        # Telegram on start + result (no-op if not configured).
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        notify(f"🌙 auto-sum start: {tid}" + (f" (≤{limit})" if limit else ""))
        rc = run_auto_sum(tid, limit=limit)
        refresh_index(tid)  # 新总结/重做版进语义索引(A2)
        notify(burn_down_msg(tid, rc, limit))  # 单主题燃尽报告(2026-06-17)
        sys.exit(rc)
    if stage == "auto-sum-next":
        # 队列模式:从 topics 表按 priority 挑第一个还有活的主题跑,做完自动顺到下一个。
        # cron 只挂这一个,不写死主题;加新主题自动进队,优先级在 topics.priority。
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        target = select_next_topic()
        if target is None:
            notify("🎉 auto-sum-next: 队列所有主题已总结完,无剩余\n" + queue_report())
            sys.exit(0)
        done_before, _, _ = topic_progress(target)
        notify(f"🌙 auto-sum start: {target} (≤{limit}) [队列选中]")
        rc = run_auto_sum(target, limit=limit)
        refresh_index(target)  # 新总结/重做版进语义索引(A2)
        done_after, doable_after, _ = topic_progress(target)
        msg = burn_down_msg(target, rc, limit)
        if done_after == done_before and doable_after > 0:
            msg += "\n⚠️ 本轮 0 进展(可能卡坏PDF),队列未推进——需人工看"
        notify(msg + "\n" + queue_report())
        sys.exit(rc)
    rc = run_stage(stage, tid)
    if stage in ("sum", "finalize", "verify") and rc == 0:
        refresh_index(tid)  # 单跑这些阶段也刷新语义索引(A2)
    sys.exit(rc)


if __name__ == "__main__":
    main()
