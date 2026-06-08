// Reusable DB-write helpers (paper upsert, topic upsert, citations).
'use strict';
const { uniqueSlug } = require('./slug');
const nowISO = () => new Date().toISOString();

// Insert a paper into the global store if new; otherwise enrich metadata only.
// NEVER touches status / pdf_path / summarized_at (preserves prior work).
function upsertPaper(db, p) {
  const existing = db.prepare('SELECT id, sources FROM papers WHERE id=?').get(p.id);
  const ext = JSON.stringify(p.ext_ids || {});
  const refs = JSON.stringify(p.ref_ext_ids || []);
  const authors = JSON.stringify(p.authors || []);
  const srcs = JSON.stringify(p.sources || []);
  if (!existing) {
    const slug = uniqueSlug(db, p.title, p.id);
    db.prepare(
      `INSERT INTO papers (id,doi,slug,title,authors,year,venue,abstract,language,citation_count,
        is_oa,oa_url,landing_url,sources,ext_ids,ref_ext_ids,status,is_edge,discovered_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'discovered', ?, ?)`
    ).run(p.id, p.doi, slug, p.title, authors, p.year, p.venue, p.abstract, p.language,
      p.citation_count || 0, p.is_oa ? 1 : 0, p.oa_url, p.landing_url, srcs, ext, refs,
      p.is_edge ? 1 : 0, nowISO());
    return 'new';
  }
  const mergedSources = JSON.stringify([
    ...new Set([...(JSON.parse(existing.sources || '[]')), ...(p.sources || [])]),
  ]);
  db.prepare(
    `UPDATE papers SET citation_count=MAX(citation_count,?), is_oa=MAX(is_oa,?),
       oa_url=COALESCE(oa_url,?), abstract=COALESCE(abstract,?), venue=COALESCE(venue,?),
       sources=?, ext_ids=? WHERE id=?`
  ).run(p.citation_count || 0, p.is_oa ? 1 : 0, p.oa_url, p.abstract, p.venue,
    mergedSources, ext, p.id);
  return 'existing';
}

function upsertTopic(db, topic, target) {
  db.prepare(
    `INSERT INTO topics (id,title,idea,queries,window_years,target,created_at,last_run_at)
     VALUES (?,?,?,?,?,?,?,?)
     ON CONFLICT(id) DO UPDATE SET title=excluded.title, idea=excluded.idea,
       queries=excluded.queries, last_run_at=excluded.last_run_at`
  ).run(topic.id, topic.title, topic.idea, JSON.stringify(topic.queries || []),
    topic.window_years || 20, target, nowISO(), nowISO());
}

function setPaperTopic(db, topicId, p, rank) {
  db.prepare(
    `INSERT INTO paper_topic (topic_id,paper_id,relevance,relevance_reason,matched_queries,rank,added_at)
     VALUES (?,?,?,?,?,?,?)
     ON CONFLICT(topic_id,paper_id) DO UPDATE SET relevance=excluded.relevance,
       relevance_reason=excluded.relevance_reason, rank=excluded.rank`
  ).run(topicId, p.id, p.relevance ?? null, p.relevance_reason ?? null,
    JSON.stringify(p.matched_queries || []), rank, nowISO());
}

// Build internal citation edges from OpenAlex referenced_works among the given set.
function buildCitations(db, papers) {
  const oaToId = new Map();
  for (const p of papers) if (p.ext_ids && p.ext_ids.openalex) oaToId.set(p.ext_ids.openalex, p.id);
  const ins = db.prepare('INSERT OR IGNORE INTO citations (src_paper_id,dst_paper_id) VALUES (?,?)');
  let edges = 0;
  for (const p of papers)
    for (const ref of p.ref_ext_ids || []) {
      const dst = oaToId.get(ref);
      if (dst && dst !== p.id) { ins.run(p.id, dst); edges++; }
    }
  return edges;
}

module.exports = { upsertPaper, upsertTopic, setPaperTopic, buildCitations, nowISO };
