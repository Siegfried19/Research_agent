// Phase 3a: build a summarization worklist for a topic (papers with a PDF, not yet summarized).
// Usage: node --experimental-sqlite pipeline/build_worklist.js <topicId>
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');

const fileId = (id) => id.replace(/[^a-z0-9._-]/gi, '_').slice(0, 180);

function main() {
  const topicId = process.argv[2];
  if (!topicId) { console.error('usage: build_worklist.js <topicId>'); process.exit(1); }
  const db = open();
  const rows = db.prepare(
    `SELECT p.*, pt.relevance, pt.relevance_reason
       FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
      WHERE pt.topic_id=? AND p.status='pdf_downloaded'
      ORDER BY pt.rank`).all(topicId);
  db.close();

  const work = rows.map((r) => {
    const sdir = path.join(ROOT, 'store', 'summaries', r.slug || fileId(r.id));
    return {
      id: r.id,
      title: r.title,
      authors: JSON.parse(r.authors || '[]'),
      year: r.year,
      venue: r.venue,
      citation_count: r.citation_count,
      doi: r.doi,
      landing_url: r.landing_url,
      is_edge: !!r.is_edge,
      relevance: r.relevance,
      relevance_reason: r.relevance_reason,
      text_path: r.text_path ? path.join(ROOT, r.text_path) : null,
      pdf_path: r.pdf_path ? path.join(ROOT, r.pdf_path) : null,
      summary_dir: sdir,
      summary_path: path.join(sdir, 'v1.md'),
    };
  });

  const out = path.join(ROOT, 'topics', topicId, 'summarize_worklist.json');
  fs.writeFileSync(out, JSON.stringify({ topicId, total: work.length, work }, null, 2));
  console.log(`worklist: ${work.length} papers -> topics/${topicId}/summarize_worklist.json`);
  console.log(`  with-text: ${work.filter((w) => w.text_path).length}  pdf-only: ${work.filter((w) => !w.text_path && w.pdf_path).length}`);
}
main();
