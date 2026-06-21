"""Shared SQLite access layer for the research pipeline (Python stdlib sqlite3)."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    """ISO-8601 UTC with milliseconds + 'Z' (matches the old JS new Date().toISOString())."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

ROOT = Path(__file__).resolve().parents[2]
# RESEARCH_DB lets tests point at a throwaway DB without touching data-base/papers.sqlite.
DB_PATH = Path(os.environ["RESEARCH_DB"]) if os.environ.get("RESEARCH_DB") else ROOT / "data-base" / "papers.sqlite"
PIPELINE_DIR = ROOT / "pipeline"
CONFIG_PATH = PIPELINE_DIR / "config.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
  id              TEXT PRIMARY KEY,
  doi             TEXT,
  slug            TEXT,
  title           TEXT NOT NULL,
  authors         TEXT,
  year            INTEGER,
  venue           TEXT,
  abstract        TEXT,
  language        TEXT,
  citation_count  INTEGER DEFAULT 0,
  is_oa           INTEGER DEFAULT 0,
  oa_url          TEXT,
  landing_url     TEXT,
  sources         TEXT,
  ext_ids         TEXT,
  ref_ext_ids     TEXT,
  pdf_path        TEXT,
  text_path       TEXT,  -- DEPRECATED(2026-06-16):不再抽存 store/text,此列恒为 NULL;留列免动 prod 库
  status          TEXT DEFAULT 'discovered',
  is_edge         INTEGER DEFAULT 0,
  discovered_at   TEXT,
  pdf_fetched_at  TEXT,
  summarized_at   TEXT
);
CREATE TABLE IF NOT EXISTS topics (
  id            TEXT PRIMARY KEY,
  title         TEXT,
  idea          TEXT,
  queries       TEXT,
  window_years  INTEGER DEFAULT 20,
  target        INTEGER DEFAULT 200,
  created_at    TEXT,
  last_run_at   TEXT,
  priority      INTEGER DEFAULT 0   -- auto-sum-next 队列排序:高在前,同则按建立序(rowid)
);
CREATE TABLE IF NOT EXISTS paper_topic (
  topic_id         TEXT,
  paper_id         TEXT,
  relevance        REAL,
  relevance_reason TEXT,
  matched_queries  TEXT,
  rank             INTEGER,
  facet            TEXT,  -- 该篇在本主题下的子方向(find 阶段定;非 faceted 主题/旧行=NULL,读时当 '_all');留给 retrieve 按 facet 过滤
  added_at         TEXT,
  PRIMARY KEY (topic_id, paper_id)
);
CREATE TABLE IF NOT EXISTS summary_versions (
  paper_id    TEXT,
  version     INTEGER,
  path        TEXT,
  based_on    TEXT,
  note        TEXT,
  created_at  TEXT,
  PRIMARY KEY (paper_id, version)
);
CREATE TABLE IF NOT EXISTS citations (
  src_paper_id TEXT,
  dst_paper_id TEXT,
  PRIMARY KEY (src_paper_id, dst_paper_id)
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_papers_slug   ON papers(slug);
CREATE INDEX IF NOT EXISTS idx_papers_doi    ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_pt_topic      ON paper_topic(topic_id);
CREATE INDEX IF NOT EXISTS idx_pt_paper      ON paper_topic(paper_id);
CREATE INDEX IF NOT EXISTS idx_cit_dst       ON citations(dst_paper_id);
"""

ADD_COLUMNS = [("papers", "slug", "TEXT"),
               ("papers", "quality_tier", "TEXT"),      # block/suspect/flag/ok/trusted (lib/quality.py)
               ("papers", "quality_signals", "TEXT"),    # 逗号分隔的命中信号
               ("topics", "priority", "INTEGER DEFAULT 0"),  # auto-sum-next 队列排序
               ("paper_topic", "facet", "TEXT")]  # find 子方向落盘,供 retrieve 用(2026-06-21)


def _ensure_columns(conn):
    for table, col, coltype in ADD_COLUMNS:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")


def open_db():
    """Open (and migrate) the database. Returns a sqlite3.Connection with Row rows."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    _ensure_columns(conn)
    conn.executescript(INDEXES)
    conn.commit()
    return conn


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
