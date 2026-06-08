// Shared SQLite access layer for the research pipeline.
// Uses Node's built-in node:sqlite (run node with --experimental-sqlite).
'use strict';

const { DatabaseSync } = require('node:sqlite');
const path = require('node:path');
const fs = require('node:fs');

const ROOT = path.resolve(__dirname, '..', '..');
const DB_PATH = path.join(ROOT, 'db', 'papers.sqlite');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS papers (
  id              TEXT PRIMARY KEY,   -- normalized DOI, or "arxiv:..", or "title:<hash>"
  doi             TEXT,
  slug            TEXT,               -- human-readable title slug, used for file naming
  title           TEXT NOT NULL,
  authors         TEXT,               -- JSON array of names
  year            INTEGER,
  venue           TEXT,
  abstract        TEXT,
  language        TEXT,
  citation_count  INTEGER DEFAULT 0,
  is_oa           INTEGER DEFAULT 0,
  oa_url          TEXT,
  landing_url     TEXT,
  sources         TEXT,               -- JSON array: ["openalex","arxiv",...]
  ext_ids         TEXT,               -- JSON: {openalex,s2,arxiv,pmid,...}
  ref_ext_ids     TEXT,               -- JSON array of referenced-work external ids
  pdf_path        TEXT,
  text_path       TEXT,
  status          TEXT DEFAULT 'discovered', -- discovered|pdf_downloaded|pdf_failed|summarized
  is_edge         INTEGER DEFAULT 0,  -- flagged low-citation / marginal
  discovered_at   TEXT,
  pdf_fetched_at  TEXT,
  summarized_at   TEXT
);

CREATE TABLE IF NOT EXISTS topics (
  id            TEXT PRIMARY KEY,     -- slug
  title         TEXT,
  idea          TEXT,                 -- full research-idea text
  queries       TEXT,                 -- JSON array of generated query strings
  window_years  INTEGER DEFAULT 20,
  target        INTEGER DEFAULT 200,
  created_at    TEXT,
  last_run_at   TEXT
);

CREATE TABLE IF NOT EXISTS paper_topic (
  topic_id         TEXT,
  paper_id         TEXT,
  relevance        REAL,              -- 0..100
  relevance_reason TEXT,
  matched_queries  TEXT,              -- JSON array
  rank             INTEGER,
  added_at         TEXT,
  PRIMARY KEY (topic_id, paper_id)
);

CREATE TABLE IF NOT EXISTS summary_versions (
  paper_id    TEXT,
  version     INTEGER,
  path        TEXT,
  based_on    TEXT,                   -- JSON array of paper_ids that informed this version
  note        TEXT,
  created_at  TEXT,
  PRIMARY KEY (paper_id, version)
);

CREATE TABLE IF NOT EXISTS citations (
  src_paper_id TEXT,                  -- citing paper
  dst_paper_id TEXT,                  -- cited paper
  PRIMARY KEY (src_paper_id, dst_paper_id)
);

`;

// Indexes run after column-ensure (a fresh-vs-migrated table may lack new columns).
const INDEXES = `
CREATE INDEX IF NOT EXISTS idx_papers_slug   ON papers(slug);
CREATE INDEX IF NOT EXISTS idx_papers_doi    ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_pt_topic      ON paper_topic(topic_id);
CREATE INDEX IF NOT EXISTS idx_pt_paper      ON paper_topic(paper_id);
CREATE INDEX IF NOT EXISTS idx_cit_dst       ON citations(dst_paper_id);
`;

// Idempotent additive migrations for DBs created before a column existed.
const ADD_COLUMNS = [['papers', 'slug', 'TEXT']];
function ensureColumns(db) {
  for (const [table, col, type] of ADD_COLUMNS) {
    const cols = db.prepare(`PRAGMA table_info(${table})`).all().map((c) => c.name);
    if (!cols.includes(col)) db.exec(`ALTER TABLE ${table} ADD COLUMN ${col} ${type}`);
  }
}

function open() {
  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  const db = new DatabaseSync(DB_PATH);
  db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA foreign_keys = ON;');
  db.exec(SCHEMA);
  ensureColumns(db);
  db.exec(INDEXES);
  return db;
}

module.exports = { open, ROOT, DB_PATH };
