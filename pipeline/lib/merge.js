// Dedup + merge normalized records from multiple sources into canonical papers.
'use strict';

const crypto = require('node:crypto');

const normTitle = (t) =>
  (t || '').toLowerCase().normalize('NFKD').replace(/[^a-z0-9぀-ヿ一-鿿]+/g, ' ').trim();

function canonicalId(rec) {
  if (rec.doi) return rec.doi;
  if (rec.ext_ids && rec.ext_ids.arxiv) return 'arxiv:' + rec.ext_ids.arxiv;
  const h = crypto.createHash('sha1').update(normTitle(rec.title)).digest('hex').slice(0, 16);
  return 'title:' + h;
}

const longer = (a, b) => ((b && b.length > (a ? a.length : 0)) ? b : a);

function mergeInto(dst, rec) {
  dst.sources.add(rec.source);
  dst.relRankBySource[rec.source] = Math.min(
    dst.relRankBySource[rec.source] ?? Infinity,
    rec.relRank ?? Infinity
  );
  dst.title = dst.title || rec.title;
  dst.doi = dst.doi || rec.doi;
  dst.year = dst.year || rec.year;
  dst.venue = dst.venue || rec.venue;
  dst.abstract = longer(dst.abstract, rec.abstract);
  dst.language = dst.language || rec.language;
  dst.citation_count = Math.max(dst.citation_count || 0, rec.citation_count || 0);
  dst.is_oa = dst.is_oa || rec.is_oa;
  dst.oa_url = dst.oa_url || rec.oa_url;
  dst.landing_url = dst.landing_url || rec.landing_url;
  if (rec.authors && rec.authors.length > (dst.authors ? dst.authors.length : 0)) dst.authors = rec.authors;
  Object.assign(dst.ext_ids, Object.fromEntries(Object.entries(rec.ext_ids || {}).filter(([, v]) => v)));
  for (const r of rec.ref_ext_ids || []) dst.refSet.add(r);
  for (const q of rec._queries || []) dst.queries.add(q);
}

// records: array of normalized records, each may carry rec._queries (array of query strings)
function mergeAll(records) {
  const byId = new Map();
  const titleIndex = new Map(); // normTitle -> canonical id (to catch DOI-vs-title dupes)

  for (const rec of records) {
    let id = canonicalId(rec);
    const nt = normTitle(rec.title);
    // If a title-keyed dup already maps to a real id (or vice versa), reuse it.
    if (!byId.has(id) && nt && titleIndex.has(nt)) id = titleIndex.get(nt);

    if (!byId.has(id)) {
      byId.set(id, {
        id,
        title: '',
        doi: null,
        authors: [],
        year: null,
        venue: null,
        abstract: null,
        language: null,
        citation_count: 0,
        is_oa: false,
        oa_url: null,
        landing_url: null,
        sources: new Set(),
        relRankBySource: {},
        ext_ids: {},
        refSet: new Set(),
        queries: new Set(),
      });
    }
    mergeInto(byId.get(id), rec);
    if (nt) titleIndex.set(nt, id);
  }

  return [...byId.values()].map((p) => ({
    ...p,
    sources: [...p.sources],
    ext_ids: p.ext_ids,
    ref_ext_ids: [...p.refSet],
    queries: [...p.queries],
  }));
}

module.exports = { mergeAll, canonicalId, normTitle };
