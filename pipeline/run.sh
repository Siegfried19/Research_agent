#!/usr/bin/env bash
# Orchestrate one run of a topic through its deterministic stages.
# The two agent-workflow steps (scoring, summarizing) are launched by Claude
# between stages, using the JSON emitted by `scoreargs` / `sumargs`.
#
#   run.sh <topicId> discover     # gather candidates -> candidates.json
#   run.sh <topicId> scoreargs    # (prep) clear scores, print args for score.workflow.js
#   ...Claude runs score.workflow.js with those args...
#   run.sh <topicId> commit       # select + write DB (additive on incremental)
#   run.sh <topicId> fetch        # download OA full text
#   run.sh <topicId> worklist     # build summarize worklist
#   run.sh <topicId> sumargs      # print args for summarize.workflow.js
#   ...Claude runs summarize.workflow.js with those args...
#   run.sh <topicId> finalize     # register summaries + render topic.md
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TID="$1"; STAGE="$2"
ND="node --experimental-sqlite"

# append every stage invocation to the operation log
mkdir -p "$ROOT/logs"
logline() { printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$TID" "$*" >> "$ROOT/logs/run.log"; }
logline "stage:$STAGE start"
trap 'logline "stage:$STAGE end(rc=$?)"' EXIT

case "$STAGE" in
  discover)  $ND pipeline/discover.js "topics/$TID/topic.json" ;;
  scoreargs)
    mkdir -p "topics/$TID/scores"; rm -f "topics/$TID/scores/"*.json
    node -e "const c=require('$ROOT/topics/$TID/candidates.json');process.stdout.write(JSON.stringify({idea:c.topic.idea,file:'$ROOT/topics/$TID/candidates.json',outDir:'$ROOT/topics/$TID/scores',total:c.pool}))" ;;
  commit)    $ND pipeline/commit.js "topics/$TID" ;;
  fetch)     $ND pipeline/fetch_oa.js "$TID" ;;
  worklist)  $ND pipeline/build_worklist.js "$TID" ;;
  sumargs)
    node -e "const w=require('$ROOT/topics/$TID/summarize_worklist.json');process.stdout.write(JSON.stringify({file:'$ROOT/topics/$TID/summarize_worklist.json',total:w.total}))" ;;
  finalize)  $ND pipeline/register_summaries.js "$TID"; $ND pipeline/render_topic.js "$TID" ;;
  log)       logline "note: ${*:3}" ;;   # run.sh <id> log "<message>" — record an agent-run step
  *) echo "stages: discover | scoreargs | commit | fetch | worklist | sumargs | finalize | log"; exit 1 ;;
esac
