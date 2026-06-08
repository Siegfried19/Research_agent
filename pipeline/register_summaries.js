// Phase 3c: after the summarize workflow, register v1 summaries and mark papers summarized.
// Usage: node --experimental-sqlite pipeline/register_summaries.js <topicId|all>
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');
const nowISO = () => new Date().toISOString();
const fileId = (id) => id.replace(/[^a-z0-9._-]/gi, '_').slice(0, 180);

function main() {
  const topicId = process.argv[2] || 'all';
  const db = open();
  const rows = topicId === 'all'
    ? db.prepare(`SELECT id, slug FROM papers WHERE status='pdf_downloaded'`).all()
    : db.prepare(`SELECT p.id, p.slug FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                  WHERE pt.topic_id=? AND p.status='pdf_downloaded'`).all(topicId);

  let registered = 0, missing = 0;
  for (const { id, slug } of rows) {
    const vpath = path.join(ROOT, 'store', 'summaries', slug || fileId(id), 'v1.md');
    if (!fs.existsSync(vpath) || fs.statSync(vpath).size < 100) { missing++; continue; }
    const rel = path.relative(ROOT, vpath);
    db.prepare(
      `INSERT OR IGNORE INTO summary_versions (paper_id,version,path,based_on,note,created_at)
       VALUES (?,?,?,?,?,?)`
    ).run(id, 1, rel, '[]', '首次总结', nowISO());
    db.prepare(`UPDATE papers SET status='summarized', summarized_at=? WHERE id=?`).run(nowISO(), id);
    registered++;
  }
  db.close();
  console.log(`registered ${registered} v1 summaries; ${missing} still missing a summary file`);
}
main();
