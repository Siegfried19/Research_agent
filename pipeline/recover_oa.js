// Option ②: recover free full text for papers we missed, WITHOUT any login.
// Strategy per paper still lacking a PDF: try Unpaywall (by DOI) then arXiv (by title).
// Usage: node --experimental-sqlite pipeline/recover_oa.js <topicId|all>
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { open, ROOT } = require('./lib/db');
const { getJSON, getText, sleep } = require('./lib/http');
const { normTitle } = require('./lib/merge');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const PDF_DIR = path.join(ROOT, config.paths.pdfs);
const TXT_DIR = path.join(ROOT, 'store', 'text');
const MAIL = 'a0904251001@gmail.com';
const nowISO = () => new Date().toISOString();

async function unpaywallPdf(doi) {
  try {
    const d = await getJSON(`https://api.unpaywall.org/v2/${encodeURIComponent(doi)}?email=${MAIL}`, { timeout: 30000 });
    const locs = [d.best_oa_location, ...(d.oa_locations || [])].filter(Boolean);
    for (const l of locs) if (l.url_for_pdf) return l.url_for_pdf;
  } catch {}
  return null;
}

async function arxivPdfByTitle(title) {
  try {
    const xml = await getText(
      `https://export.arxiv.org/api/query?search_query=ti:%22${encodeURIComponent(title.slice(0, 120))}%22&max_results=3`,
      { timeout: 30000 });
    const entries = xml.split('<entry>').slice(1);
    for (const e of entries) {
      const t = (e.match(/<title>([\s\S]*?)<\/title>/i) || [])[1] || '';
      const id = (e.match(/<id>([\s\S]*?)<\/id>/i) || [])[1] || '';
      if (normTitle(t) === normTitle(title)) {
        const ax = id.replace(/^https?:\/\/arxiv\.org\/abs\//, '').replace(/v\d+$/, '');
        if (ax) return `https://arxiv.org/pdf/${ax}`;
      }
    }
  } catch {}
  return null;
}

async function download(url, dest) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), config.download.timeout_ms);
  try {
    const res = await fetch(url, { headers: { 'User-Agent': config.download.user_agent, Accept: 'application/pdf,*/*' }, redirect: 'follow', signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.slice(0, 5).toString('latin1') !== '%PDF-') throw new Error('not a PDF');
    fs.writeFileSync(dest, buf);
    return buf.length;
  } finally { clearTimeout(t); }
}

async function main() {
  const topicId = process.argv[2] || 'all';
  fs.mkdirSync(PDF_DIR, { recursive: true }); fs.mkdirSync(TXT_DIR, { recursive: true });
  const db = open();
  const rows = topicId === 'all'
    ? db.prepare(`SELECT * FROM papers WHERE pdf_path IS NULL AND status IN ('pdf_failed','discovered')`).all()
    : db.prepare(`SELECT p.* FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                  WHERE pt.topic_id=? AND p.pdf_path IS NULL AND p.status IN ('pdf_failed','discovered') ORDER BY pt.rank`).all(topicId);

  console.log(`# Recover free OA: ${rows.length} papers lacking full text`);
  const upd = db.prepare(`UPDATE papers SET pdf_path=?, text_path=?, status=?, pdf_fetched_at=? WHERE id=?`);
  let recovered = 0;

  for (const r of rows) {
    const base = r.slug || r.id.replace(/[^a-z0-9._-]/gi, '_').slice(0, 180);
    const pdfPath = path.join(PDF_DIR, base + '.pdf');
    const txtPath = path.join(TXT_DIR, base + '.txt');
    let url = null, via = null;
    if (r.doi) { url = await unpaywallPdf(r.doi); if (url) via = 'unpaywall'; }
    if (!url) { url = await arxivPdfByTitle(r.title); if (url) via = 'arxiv-title'; }
    if (!url) { console.log(`  --   no free source: ${(r.title || '').slice(0, 50)}`); await sleep(500); continue; }
    try {
      const bytes = await download(url, pdfPath);
      let tpath = null;
      try { execFileSync('pdftotext', ['-q', '-enc', 'UTF-8', pdfPath, txtPath], { timeout: 60000 });
        if (fs.existsSync(txtPath) && fs.statSync(txtPath).size > 200) tpath = path.relative(ROOT, txtPath); } catch {}
      upd.run(path.relative(ROOT, pdfPath), tpath, 'pdf_downloaded', nowISO(), r.id);
      recovered++;
      console.log(`  OK [${via}, ${(bytes/1024|0)}KB] ${(r.title || '').slice(0, 48)}`);
    } catch (e) {
      console.log(`  FAIL [${via}: ${e.message}] ${(r.title || '').slice(0, 44)}`);
    }
    await sleep(config.download.delay_ms);
  }
  db.close();
  console.log(`\n# Recovered ${recovered}/${rows.length} for free. (rest -> Tier B paywall)`);
}
main().catch((e) => { console.error(e); process.exit(1); });
