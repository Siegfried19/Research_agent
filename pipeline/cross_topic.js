// Phase 6 (data): find papers shared across topics + citation bridges between topics.
// Writes store/cross_topic.json (input for the cross-topic ideas workflow).
// Usage: node --experimental-sqlite pipeline/cross_topic.js
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');

function main() {
  const db = open();
  const topics = db.prepare('SELECT id, title FROM topics').all();
  const titleById = new Map(topics.map((t) => [t.id, t.title]));

  // topics per paper
  const pt = db.prepare('SELECT paper_id, topic_id, relevance FROM paper_topic').all();
  const topicsByPaper = new Map();
  for (const r of pt) {
    if (!topicsByPaper.has(r.paper_id)) topicsByPaper.set(r.paper_id, []);
    topicsByPaper.get(r.paper_id).push({ topic: r.topic_id, relevance: r.relevance });
  }
  const paperMeta = new Map(
    db.prepare('SELECT id, title, year FROM papers').all().map((p) => [p.id, p]));

  const shared = [];
  for (const [pid, tps] of topicsByPaper) {
    if (tps.length >= 2) {
      const m = paperMeta.get(pid) || {};
      shared.push({ id: pid, title: m.title, year: m.year, topics: tps });
    }
  }

  // cross-topic citation bridges: edge whose endpoints belong to different topic sets
  const firstTopic = (pid) => (topicsByPaper.get(pid) || []).map((x) => x.topic);
  const bridges = [];
  for (const e of db.prepare('SELECT src_paper_id s, dst_paper_id d FROM citations').all()) {
    const st = new Set(firstTopic(e.s)), dt = new Set(firstTopic(e.d));
    const different = [...dt].some((t) => !st.has(t)) || [...st].some((t) => !dt.has(t));
    if (st.size && dt.size && different) {
      bridges.push({
        src: e.s, dst: e.d,
        src_title: (paperMeta.get(e.s) || {}).title, dst_title: (paperMeta.get(e.d) || {}).title,
        src_topics: [...st], dst_topics: [...dt],
      });
    }
  }
  db.close();

  const out = { generated_topics: topics.length, shared_papers: shared, citation_bridges: bridges };
  fs.mkdirSync(path.join(ROOT, 'store'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, 'store', 'cross_topic.json'), JSON.stringify(out, null, 2));
  console.log(`# Cross-topic analysis (${topics.length} topics)`);
  console.log(`  shared papers (in >=2 topics): ${shared.length}`);
  console.log(`  cross-topic citation bridges: ${bridges.length}`);
  if (topics.length < 2) console.log(`  (need >=2 topics for meaningful cross-topic comparison)`);
  console.log(`  -> store/cross_topic.json`);
}
main();
