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

Only `tierb` ever needs you (to click a Cloudflare/Duo challenge).
"""
import subprocess
import sys
from pathlib import Path

from lib.db import ROOT
from lib.log import run_log

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
              "stages: discover|score|commit|fetch|recover|hunt|tierb|worklist|sum|finalize|auto", file=sys.stderr)
        sys.exit(1)
    tid, stage = sys.argv[1], sys.argv[2]
    if stage == "auto":
        for s in AUTO:
            print(f"=== [auto] stage: {s} ===")
            rc = run_stage(s, tid)
            if rc != 0:
                print(f"[auto] stage {s} failed (rc={rc})", file=sys.stderr)
                sys.exit(rc)
        return
    sys.exit(run_stage(stage, tid))


if __name__ == "__main__":
    main()
