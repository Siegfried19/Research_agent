// One-time migration: add slug column, backfill, rename files to title-based names, fix paths.
// Usage: node --experimental-sqlite pipeline/migrate_slugs.js
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');
const { uniqueSlug } = require('./lib/slug');

const oldFileId = (id) => id.replace(/[^a-z0-9._-]/gi, '_').slice(0, 180);
const mv = (a, b) => { if (fs.existsSync(a) && a !== b) { fs.mkdirSync(path.dirname(b), { recursive: true }); fs.renameSync(a, b); return true; } return false; };

function main() {
  const db = open();
  const cols = db.prepare('PRAGMA table_info(papers)').all().map((c) => c.name);
  if (!cols.includes('slug')) db.exec('ALTER TABLE papers ADD COLUMN slug TEXT');

  const papers = db.prepare('SELECT id, title, slug, pdf_path, text_path FROM papers ORDER BY discovered_at').all();
  let renamedFiles = 0, sluggedRows = 0;

  for (const p of papers) {
    const slug = p.slug || uniqueSlug(db, p.title, p.id);
    if (!p.slug) { db.prepare('UPDATE papers SET slug=? WHERE id=?').run(slug, p.id); sluggedRows++; }

    const oldBase = oldFileId(p.id);
    // pdf
    if (mv(path.join(ROOT, 'store/pdfs', oldBase + '.pdf'), path.join(ROOT, 'store/pdfs', slug + '.pdf'))) renamedFiles++;
    // text
    if (mv(path.join(ROOT, 'store/text', oldBase + '.txt'), path.join(ROOT, 'store/text', slug + '.txt'))) renamedFiles++;
    // summary dir
    if (mv(path.join(ROOT, 'store/summaries', oldBase), path.join(ROOT, 'store/summaries', slug))) renamedFiles++;

    // fix DB paths
    const newPdf = path.join('store/pdfs', slug + '.pdf');
    const newTxt = path.join('store/text', slug + '.txt');
    if (p.pdf_path) db.prepare('UPDATE papers SET pdf_path=? WHERE id=?').run(newPdf, p.id);
    if (p.text_path) db.prepare('UPDATE papers SET text_path=? WHERE id=?').run(newTxt, p.id);
    // fix summary_versions paths
    for (const sv of db.prepare('SELECT version, path FROM summary_versions WHERE paper_id=?').all(p.id)) {
      const fn = path.basename(sv.path);
      db.prepare('UPDATE summary_versions SET path=? WHERE paper_id=? AND version=?')
        .run(path.join('store/summaries', slug, fn), p.id, sv.version);
    }
  }
  db.close();
  console.log(`migrated: ${sluggedRows} rows slugged, ${renamedFiles} files/dirs renamed`);
}
main();
