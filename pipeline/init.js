// Phase 0: create directory structure + initialize the SQLite database.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT, DB_PATH } = require('./lib/db');

const dirs = [
  'db',
  'store/pdfs',
  'store/summaries',
  'store/text',
  'topics',
  'runs',
];

for (const d of dirs) {
  fs.mkdirSync(path.join(ROOT, d), { recursive: true });
}

const db = open();
const tables = db
  .prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
  .all()
  .map((r) => r.name);
db.close();

console.log('Initialized research pipeline.');
console.log('  root :', ROOT);
console.log('  db   :', DB_PATH);
console.log('  dirs :', dirs.join(', '));
console.log('  tables:', tables.join(', '));
