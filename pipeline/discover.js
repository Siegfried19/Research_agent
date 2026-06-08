// Phase 1: multi-source discovery + dedup -> candidate pool (NO db write).
// Selection of the final top-N happens after agent relevance scoring (see score/commit).
// Usage: node --experimental-sqlite pipeline/discover.js topics/<slug>/topic.json
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { ROOT } = require('./lib/db');
const sources = require('./lib/sources');
const { mergeAll } = require('./lib/merge');
const { sleep } = require('./lib/http');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));

async function gather(queries, win) {
  const all = [];
  const log = [];
  for (const q of queries) {
    for (const [name, fn] of Object.entries({
      openalex: () => sources.openalex(q, { fromDate: win.fromDate }),
      semantic_scholar: () => sources.semanticScholar(q, { fromYear: win.fromYear }),
      arxiv: () => sources.arxiv(q, { fromYear: win.fromYear }),
      pubmed: () => sources.pubmed(q, { fromYear: win.fromYear, toYear: win.toYear }),
    })) {
      if (!config.sources[name]) continue;
      try {
        const recs = await fn();
        recs.forEach((r) => (r._queries = [q]));
        all.push(...recs);
        log.push(`  [${name}] "${q.slice(0, 48)}" -> ${recs.length}`);
      } catch (e) {
        log.push(`  [${name}] "${q.slice(0, 48)}" -> ERROR ${e.message}`);
      }
      await sleep(700);
    }
  }
  return { all, log };
}

function languageOk(p) {
  if (config.language_strict) return config.languages.includes(p.language);
  return !p.language || config.languages.includes(p.language);
}

// Recall-oriented prefilter: rank by best position across sources + multi-source agreement.
// Citations are NOT used to select (they over-promote famous-but-off-topic papers);
// they are kept only for the edge flag and later tie-breaking.
function prefilterRank(papers) {
  const maxRankBySource = {};
  for (const p of papers)
    for (const [s, r] of Object.entries(p.relRankBySource))
      maxRankBySource[s] = Math.max(maxRankBySource[s] || 0, r);
  for (const p of papers) {
    let best = 0;
    for (const [s, r] of Object.entries(p.relRankBySource)) {
      const denom = (maxRankBySource[s] || 0) + 1;
      best = Math.max(best, 1 - r / denom);
    }
    const multi = Math.min(0.2, (p.sources.length - 1) * 0.1);
    p._pre = Math.min(1, best + multi);
  }
  papers.sort((a, b) => b._pre - a._pre);
  return papers;
}

async function main() {
  const topicPath = process.argv[2];
  if (!topicPath) { console.error('usage: discover.js topics/<slug>/topic.json'); process.exit(1); }
  const topic = JSON.parse(fs.readFileSync(path.resolve(topicPath), 'utf8'));
  const today = new Date();
  const fromYear = today.getFullYear() - (topic.window_years || config.window_years);
  const win = { fromYear, toYear: today.getFullYear(), fromDate: `${fromYear}-01-01` };
  const target = topic.target || config.first_run_target;
  const poolSize = Math.min(500, Math.max(target * 2, 60));

  console.log(`# Discovery: ${topic.title} (${topic.id})`);
  console.log(`  window ${win.fromDate}..${win.toYear}  target ${target}  pool ${poolSize}  queries ${topic.queries.length}`);

  const { all, log } = await gather(topic.queries, win);
  console.log(log.join('\n'));

  let papers = mergeAll(all).filter(languageOk);
  papers = prefilterRank(papers);
  const { edge_citation_threshold } = config.ranking;
  const pool = papers.slice(0, poolSize).map((p) => ({
    id: p.id, doi: p.doi, title: p.title, authors: p.authors, year: p.year,
    venue: p.venue, abstract: p.abstract, language: p.language,
    citation_count: p.citation_count, is_oa: p.is_oa, oa_url: p.oa_url,
    landing_url: p.landing_url, sources: p.sources, ext_ids: p.ext_ids,
    ref_ext_ids: p.ref_ext_ids, matched_queries: p.queries,
    is_edge: (p.citation_count || 0) < edge_citation_threshold,
    prefilter: +p._pre.toFixed(3),
  }));

  const dir = path.join(ROOT, 'topics', topic.id);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'candidates.json'), JSON.stringify({
    topic: { id: topic.id, title: topic.title, idea: topic.idea, queries: topic.queries },
    window: win, target, generated_at: today.toISOString(),
    raw_records: all.length, merged_unique: papers.length, pool: pool.length,
    candidates: pool,
  }, null, 2));

  const withAbs = pool.filter((p) => p.abstract).length;
  const oa = pool.filter((p) => p.is_oa).length;
  console.log(`\n# Result`);
  console.log(`  raw ${all.length}  merged-unique ${papers.length}  pool ${pool.length}`);
  console.log(`  pool has-abstract ${withAbs}  OA-downloadable ${oa}`);
  console.log(`  -> topics/${topic.id}/candidates.json  (next: relevance scoring)`);
}

main().catch((e) => { console.error(e); process.exit(1); });
