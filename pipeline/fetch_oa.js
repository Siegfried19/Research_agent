// Phase 2: download open-access PDFs for a topic's selected papers, extract text.
// Usage: node --experimental-sqlite pipeline/fetch_oa.js <topicId|all>
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { open, ROOT } = require('./lib/db');
const { sleep } = require('./lib/http');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const PDF_DIR = path.join(ROOT, config.paths.pdfs);
const TXT_DIR = path.join(ROOT, 'store', 'text');
const nowISO = () => new Date().toISOString();
const fileId = (id) => id.replace(/[^a-z0-9._-]/gi, '_').slice(0, 180);

async function download(url, dest, ua) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), config.download.timeout_ms);
  try {
    const res = await fetch(url, { headers: { 'User-Agent': ua, Accept: 'application/pdf,*/*' }, redirect: 'follow', signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.slice(0, 5).toString('latin1') !== '%PDF-') throw new Error('not a PDF (likely landing page)');
    fs.writeFileSync(dest, buf);
    return buf.length;
  } finally { clearTimeout(t); }
}

async function main() {
  const topicId = process.argv[2];
  if (!topicId) { console.error('usage: fetch_oa.js <topicId|all>'); process.exit(1); }
  fs.mkdirSync(PDF_DIR, { recursive: true });
  fs.mkdirSync(TXT_DIR, { recursive: true });
  const db = open();

  const rows = topicId === 'all'
    ? db.prepare(`SELECT * FROM papers WHERE is_oa=1 AND oa_url IS NOT NULL AND status='discovered'`).all()
    : db.prepare(
        `SELECT p.* FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
         WHERE pt.topic_id=? AND p.is_oa=1 AND p.oa_url IS NOT NULL AND p.status='discovered'
         ORDER BY pt.rank`).all(topicId);

  console.log(`# OA download: ${rows.length} candidates`);
  const ua = config.download.user_agent;
  let ok = 0, fail = 0, textOk = 0;
  const upd = db.prepare(`UPDATE papers SET pdf_path=?, text_path=?, status=?, pdf_fetched_at=? WHERE id=?`);

  // Build the list of URLs to try for a paper: primary oa_url, then arXiv pdf fallback.
  function urlsFor(r) {
    const urls = [];
    if (r.oa_url) urls.push(r.oa_url);
    let arxivId = null;
    try { arxivId = (JSON.parse(r.ext_ids || '{}')).arxiv; } catch {}
    if (!arxivId && r.id.startsWith('arxiv:')) arxivId = r.id.slice(6);
    if (arxivId) {
      const clean = String(arxivId).replace(/v\d+$/, '');
      const ax = `https://arxiv.org/pdf/${clean}`;
      if (!urls.includes(ax)) urls.push(ax);
    }
    return urls;
  }

  // simple sequential-with-delay loop (polite); concurrency kept low to avoid hammering hosts
  for (const r of rows) {
    const base = r.slug || fileId(r.id);
    const pdfPath = path.join(PDF_DIR, base + '.pdf');
    const txtPath = path.join(TXT_DIR, base + '.txt');
    try {
      let bytes = null, lastErr = null;
      for (const u of urlsFor(r)) {
        try { bytes = await download(u, pdfPath, ua); break; }
        catch (e) { lastErr = e; }
      }
      if (bytes === null) throw lastErr || new Error('no url');
      let tpath = null;
      try {
        execFileSync('pdftotext', ['-q', '-enc', 'UTF-8', pdfPath, txtPath], { timeout: 60000 });
        if (fs.existsSync(txtPath) && fs.statSync(txtPath).size > 200) { tpath = txtPath; textOk++; }
      } catch { /* text extraction best-effort */ }
      upd.run(path.relative(ROOT, pdfPath), tpath ? path.relative(ROOT, tpath) : null, 'pdf_downloaded', nowISO(), r.id);
      ok++;
      console.log(`  OK   [${(bytes/1024|0)}KB] ${(r.title||'').slice(0,55)}`);
    } catch (e) {
      upd.run(null, null, 'pdf_failed', nowISO(), r.id);
      fail++;
      console.log(`  FAIL [${e.message}] ${(r.title||'').slice(0,50)}`);
    }
    await sleep(config.download.delay_ms);
  }
  db.close();
  console.log(`\n# Done: ${ok} pdf, ${textOk} text extracted, ${fail} failed`);
}

main().catch((e) => { console.error(e); process.exit(1); });
