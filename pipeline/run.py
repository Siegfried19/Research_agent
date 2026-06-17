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
  verify    cross-model fact-check ALL unverified summaries (Codex), auto-correct
            majors (claude -p, vN+1) + re-check, then re-render topic.md
  auto      run all of the above, in order

  auto-pull  daytime/attended half: discover..hunt + tierb + worklist.
             Gets every PDF ready (incl. paywalled — you click tierb challenges).
             Token cost = score + hunt only (small).
  auto-sum   nightly/unattended half: sum + finalize + verify.
             The token-heavy summarize/verify, meant to run via cron while you
             sleep so it doesn't compete with your daytime Max usage. No human,
             no paywall. Idempotent — already-summarized papers are skipped, so
             a partial run just gets finished on the next night.

Only `tierb` ever needs you (to click a Cloudflare/Duo challenge) — and it lives
in `auto-pull`, the attended half. `auto-sum` is fully unattended.
"""
import subprocess
import sys
from pathlib import Path

from lib.db import ROOT
from lib.log import run_log
from lib.notify import notify

PY = sys.executable
PDIR = ROOT / "pipeline"

# stage -> list of (script, [args...]) run in order
def steps(stage, tid):
    return {
        "discover": [("stages/discover.py", [f"topics/{tid}/topic.json"])],
        "score":    [("stages/score_auto.py", [tid])],
        "commit":   [("stages/commit.py", [f"topics/{tid}"])],
        "fetch":    [("stages/fetch_oa.py", [tid])],
        "recover":  [("stages/recover_oa.py", [tid])],
        "hunt":     [("stages/recover_agent.py", [tid])],
        "tierb":    [("stages/fetch_tierb.py", [tid])],
        "worklist": [("stages/build_worklist.py", [tid])],
        "sum":      [("stages/summarize_auto.py", [tid])],
        "finalize": [("stages/register_summaries.py", [tid]), ("stages/render_topic.py", [tid])],
        "verify":   [("stages/escalate_verify.py", [tid, "--start-pct", "100"]),
                     ("stages/render_topic.py", [tid])],
    }.get(stage)


AUTO = ["discover", "score", "commit", "fetch", "recover", "hunt", "tierb", "worklist", "sum", "finalize", "verify"]
# Token-aware split (2026-06-16): pull half is attended (tierb) + small token cost;
# sum half is the token-heavy summarize/verify, meant for an unattended nightly cron.
AUTO_PULL = ["discover", "score", "commit", "fetch", "recover", "hunt", "tierb", "worklist"]
AUTO_SUM = ["sum", "finalize", "verify"]


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
    """Nightly unattended half: sum -> finalize -> verify. continue-on-error
    (idempotent stages; partial progress finished next night). When limit is
    set, only that many papers are summarized this run — the verify stage still
    sweeps whatever's unverified but is bounded over time by the per-run cap and
    its own codex usage-limit circuit breaker."""
    sum_args = [tid, str(concurrency)]
    if limit:
        sum_args += ["--limit", str(limit)]
    chain = [
        ("sum",      [("stages/summarize_auto.py", sum_args)]),
        ("finalize", steps("finalize", tid)),
        ("verify",   steps("verify", tid)),
    ]
    final_rc = 0
    for name, step_list in chain:
        print(f"=== stage: {name} ===")
        rc = run_steps(name, tid, step_list)
        if rc != 0:
            print(f"[auto-sum] stage {name} failed (rc={rc})", file=sys.stderr)
            final_rc = rc  # keep going
    return final_rc


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
              "stages: discover|score|commit|fetch|recover|hunt|tierb|worklist|sum|finalize|verify\n"
              "        auto (all) | auto-pull (attended half) | auto-sum [N] (nightly cron, cap N/run)", file=sys.stderr)
        sys.exit(1)
    tid, stage = sys.argv[1], sys.argv[2]
    if stage == "auto":
        sys.exit(run_chain(AUTO, tid))
    if stage == "auto-pull":
        sys.exit(run_chain(AUTO_PULL, tid))
    if stage == "auto-sum":
        # unattended nightly cron: sum -> finalize -> verify, continue-on-error.
        # Optional batch size: `auto-sum <N>` caps this run to N new summaries
        # (e.g. 10) so it fits one token window; run it twice a night ~4.5h apart
        # via two cron lines to land each batch in a fresh quota window.
        # Telegram on start + result (no-op if not configured).
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        notify(f"🌙 auto-sum start: {tid}" + (f" (≤{limit})" if limit else ""))
        rc = run_auto_sum(tid, limit=limit)
        notify(f"{'✅' if rc == 0 else '⚠️'} auto-sum done: {tid} (rc={rc})")
        sys.exit(rc)
    sys.exit(run_stage(stage, tid))


if __name__ == "__main__":
    main()
