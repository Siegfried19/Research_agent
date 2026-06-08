// Phase 5a (commit): record new summary versions produced by update.workflow.js.
// Usage: node --experimental-sqlite pipeline/register_updates.js
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');
const nowISO = () => new Date().toISOString();

function main() {
  const wl = path.join(ROOT, 'store', 'update_worklist.json');
  if (!fs.existsSync(wl)) { console.error('no update_worklist.json'); process.exit(1); }
  const { work } = JSON.parse(fs.readFileSync(wl, 'utf8'));
  const db = open();
  let n = 0, missing = 0;
  for (const w of work) {
    if (!fs.existsSync(w.outPath) || fs.statSync(w.outPath).size < 100) { missing++; continue; }
    const rel = path.relative(ROOT, w.outPath);
    const basedOn = JSON.stringify((w.related || []).map((r) => r.id));
    db.prepare(
      `INSERT OR IGNORE INTO summary_versions (paper_id,version,path,based_on,note,created_at)
       VALUES (?,?,?,?,?,?)`
    ).run(w.paperId, w.nextVersion, rel, basedOn, `基于 ${w.related.length} 篇相关论文更新`, nowISO());
    db.prepare('UPDATE papers SET summarized_at=? WHERE id=?').run(nowISO(), w.paperId);
    n++;
  }
  db.close();
  console.log(`registered ${n} updated versions; ${missing} missing output`);
}
main();
