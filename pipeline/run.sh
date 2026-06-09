#!/usr/bin/env bash
# Thin shim -> Python orchestrator (the pipeline is Python now; see run.py).
# Usage: bash pipeline/run.sh <topicId> <stage>   (stage: discover|score|commit|
#   fetch|recover|tierb|worklist|sum|finalize|auto)
exec python3 "$(dirname "$0")/run.py" "$@"
