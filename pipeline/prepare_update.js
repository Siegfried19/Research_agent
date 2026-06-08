// Phase 5a (prep): build an update worklist to re-summarize papers in light of related work.
// Usage:
//   node --experimental-sqlite pipeline/prepare_update.js <paperId> [<paperId> ...]
//   node --experimental-sqlite pipeline/prepare_update.js --related <relId,relId> <paperId>
// If no --related given, related papers default to summarized citation-neighbors.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');

function latestVersion(db, id) {
  const r = db.prepare('SELECT MAX(version) v, path FROM summary_versions WHERE paper_id=?').get(id);
  const vrow = db.prepare('SELECT version, path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1').get(id);
  return vrow || null;
}

function citationNeighbors(db, id) {
  const out = new Set();
  for (const r of db.prepare('SELECT dst_paper_id x FROM citations WHERE src_paper_id=?').all(id)) out.add(r.x);
  for (const r of db.prepare('SELECT src_paper_id x FROM citations WHERE dst_paper_id=?').all(id)) out.add(r.x);
  return [...out];
}

function main() {
  const argv = process.argv.slice(2);
  let explicitRelated = null;
  const ids = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--related') { explicitRelated = argv[++i].split(',').map((s) => s.trim()).filter(Boolean); }
    else ids.push(argv[i]);
  }
  if (!ids.length) { console.error('usage: prepare_update.js <paperId> [...] [--related id,id]'); process.exit(1); }

  const db = open();
  const work = [];
  for (const id of ids) {
    const p = db.prepare('SELECT id, slug, title FROM papers WHERE id=?').get(id);
    if (!p) { console.log(`skip (not in db): ${id}`); continue; }
    const cur = latestVersion(db, id);
    if (!cur) { console.log(`skip (no existing summary): ${id}`); continue; }
    const relIds = (explicitRelated || citationNeighbors(db, id))
      .filter((r) => r !== id)
      .filter((r) => db.prepare("SELECT 1 FROM papers WHERE id=? AND status='summarized'").get(r));
    if (!relIds.length) { console.log(`skip (no summarized related papers): ${(p.title||'').slice(0,40)}`); continue; }
    const related = relIds.map((r) => {
      const rp = db.prepare('SELECT title, slug FROM papers WHERE id=?').get(r);
      const sv = db.prepare('SELECT path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1').get(r);
      return { id: r, title: rp && rp.title, path: sv ? path.join(ROOT, sv.path) : null };
    }).filter((r) => r.path);
    const nextVersion = cur.version + 1;
    const outPath = path.join(ROOT, 'store', 'summaries', p.slug, `v${nextVersion}.md`);
    work.push({
      paperId: id, title: p.title,
      currentVersion: cur.version, currentPath: path.join(ROOT, cur.path),
      nextVersion, outPath,
      related,
    });
  }
  db.close();

  const out = path.join(ROOT, 'store', 'update_worklist.json');
  fs.writeFileSync(out, JSON.stringify({ total: work.length, work }, null, 2));
  console.log(`update worklist: ${work.length} papers -> store/update_worklist.json`);
  for (const w of work) console.log(`  v${w.currentVersion}->v${w.nextVersion}  ${w.related.length} related  ${(w.title||'').slice(0,45)}`);
}
main();
