"""Logging — a first-class citizen of this pipeline.

Two layers, both append-only:
  - logs/run.log         machine log: one tab-separated line per stage/event
                         (continuous with the old run.sh history; same format)
  - logs/pipeline-<date>.log   detailed per-day log (everything a script prints
                         through its logger also lands here)

Usage:
  from lib.log import get_logger, run_log, stage
  log = get_logger("discover")
  log.info("...")                      # -> console + daily file
  run_log(topic_id, "stage:discover start")
  with stage(topic_id, "discover"):    # logs start + end(rc=…) like the old trap
      ...
"""
import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .db import ROOT

LOG_DIR = ROOT / "logs"
RUN_LOG = LOG_DIR / "run.log"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_log(topic_id, msg):
    """Append one tab-separated line to logs/run.log (machine log)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{_now()}\t{topic_id or '-'}\t{msg}\n")


_configured = set()


def get_logger(name):
    """Logger that writes to console (stderr) AND logs/pipeline-<date>.log."""
    logger = logging.getLogger(name)
    if name in _configured:
        return logger
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    daily = LOG_DIR / f"pipeline-{datetime.now().strftime('%Y-%m-%d')}.log"
    fh = logging.FileHandler(daily, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False
    _configured.add(name)
    return logger


@contextmanager
def stage(topic_id, name):
    """Mirror the old run.sh trap: log stage start, and end with a return code."""
    run_log(topic_id, f"stage:{name} start")
    rc = 0
    try:
        yield
    except BaseException:
        rc = 1
        raise
    finally:
        run_log(topic_id, f"stage:{name} end(rc={rc})")
