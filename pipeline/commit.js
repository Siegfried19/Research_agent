// After relevance scoring: merge scores, select, write to DB (additive on incremental runs).
// Usage: node --experimental-sqlite pipeline/commit.js topics/<slug>
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');
const store = require('./lib/store');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));

function main() {
  const topicDir = path.resolve(process.argv[2]);
  const cand = JSON.parse(fs.readFileSync(path.join(topicDir, 'candidates.json'), 'utf8'));
  const scoreDir = path.join(topicDir, 'scores');
  const topic = cand.topic;
  const target = cand.target || config.first_run_target;

  // merge all batch score files by id
  const scoreById = new Map();
  if (fs.existsSync(scoreDir))
    for (const f of fs.readdirSync(scoreDir).filter((x) => x.endsWith('.json')))
      for (const s of JSON.parse(fs.readFileSync(path.join(scoreDir, f), 'utf8'))) scoreById.set(s.id, s);

  const scored = cand.candidates.map((p) => {
    const s = scoreById.get(p.id) || {};
    return { ...p, relevance: s.relevance ?? 0, relevance_reason: s.reason || '(未打分)', edge_insight: !!s.edge_insight };
  });
  const eligible = scored.filter((p) => p.relevance >= 30 || p.edge_insight)
    .sort((a, b) => b.relevance - a.relevance || (b.citation_count || 0) - (a.citation_count || 0));

  const db = open();
  store.upsertTopic(db, topic, target);
  const existing = new Set(
    db.prepare('SELECT paper_id FROM paper_topic WHERE topic_id=?').all(topic.id).map((r) => r.paper_id));
  const incremental = existing.size > 0;

  // First run: top-N. Incremental: add ALL new eligible (capped at target*3 as a safety valve).
  let selected;
  if (!incremental) selected = eligible.slice(0, target);
  else {
    const fresh = eligible.filter((p) => !existing.has(p.id));
    const cap = target * 3;
    selected = fresh.slice(0, cap);
    if (fresh.length > cap) console.log(`  note: ${fresh.length} new eligible, capped to ${cap}`);
  }

  let nNew = 0, nExisting = 0, nOA = 0, nEdge = 0;
  for (const p of selected) {
    const r = store.upsertPaper(db, p);
    if (r === 'new') nNew++; else nExisting++;
    if (p.is_oa) nOA++;
    if (p.edge_insight) nEdge++;
    store.setPaperTopic(db, topic.id, p, 0); // rank recomputed below
  }
  // also (re)write relevance for any selected that already existed in topic? selected excludes existing on incremental.

  // recompute ranks across the whole topic by relevance
  const allPT = db.prepare(
    `SELECT pt.paper_id, pt.relevance, p.citation_count
       FROM paper_topic pt JOIN papers p ON p.id=pt.paper_id
      WHERE pt.topic_id=? ORDER BY pt.relevance DESC, p.citation_count DESC`).all(topic.id);
  allPT.forEach((row, i) =>
    db.prepare('UPDATE paper_topic SET rank=? WHERE topic_id=? AND paper_id=?').run(i + 1, topic.id, row.paper_id));

  // citations among the full topic set (so new + old links get captured)
  const fullSet = db.prepare(
    `SELECT p.id, p.ext_ids, p.ref_ext_ids FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id WHERE pt.topic_id=?`)
    .all(topic.id)
    .map((r) => ({ id: r.id, ext_ids: JSON.parse(r.ext_ids || '{}'), ref_ext_ids: JSON.parse(r.ref_ext_ids || '[]') }));
  const edges = store.buildCitations(db, fullSet);

  const topicTotal = allPT.length;
  db.close();

  fs.writeFileSync(path.join(topicDir, 'selected.json'), JSON.stringify(
    selected.map((p) => ({ id: p.id, title: p.title, relevance: p.relevance, reason: p.relevance_reason,
      edge: p.edge_insight, is_oa: p.is_oa })), null, 2));

  console.log(`# Commit: ${topic.id}  [${incremental ? 'INCREMENTAL' : 'FIRST RUN'}]`);
  console.log(`  scored ${scoreById.size}/${cand.candidates.length}  eligible ${eligible.length}  added ${selected.length}`);
  console.log(`  topic now has ${topicTotal} papers  (new-to-db ${nNew}, reused ${nExisting}, OA ${nOA}, edge ${nEdge})`);
  console.log(`  citation edges (topic): ${edges}`);
}
main();
