// Phase 5b: after an incremental run, suggest which existing summaries are worth updating
// because new citation-neighbors have since been summarized.
// Usage: node --experimental-sqlite pipeline/suggest_updates.js <topicId|all>
'use strict';
const { open } = require('./lib/db');

function main() {
  const topicId = process.argv[2] || 'all';
  const db = open();
  const papers = topicId === 'all'
    ? db.prepare("SELECT id, title FROM papers WHERE status='summarized'").all()
    : db.prepare(`SELECT p.id, p.title FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                  WHERE pt.topic_id=? AND p.status='summarized'`).all(topicId);

  const suggestions = [];
  for (const p of papers) {
    const v = db.prepare('SELECT MAX(version) v, MAX(created_at) c FROM summary_versions WHERE paper_id=?').get(p.id);
    const since = v && v.c;
    // citation neighbors summarized after this paper's latest version
    const neigh = db.prepare(`
      SELECT DISTINCT q.id, q.title, q.summarized_at FROM papers q
      WHERE q.status='summarized' AND q.id<>?
        AND (q.id IN (SELECT dst_paper_id FROM citations WHERE src_paper_id=?)
          OR q.id IN (SELECT src_paper_id FROM citations WHERE dst_paper_id=?))
        AND (? IS NULL OR q.summarized_at > ?)`).all(p.id, p.id, p.id, since, since);
    if (neigh.length)
      suggestions.push({ id: p.id, title: p.title, currentVersion: v.v, new_related: neigh.map((n) => ({ id: n.id, title: n.title })) });
  }
  db.close();

  console.log(`# Update suggestions (${suggestions.length})`);
  for (const s of suggestions)
    console.log(`  [${s.new_related.length} new related] v${s.currentVersion} ${(s.title || '').slice(0, 50)}`);
  if (suggestions.length)
    console.log(`\nTo update, e.g.:  node --experimental-sqlite pipeline/prepare_update.js ${suggestions[0].id}`);
}
main();
