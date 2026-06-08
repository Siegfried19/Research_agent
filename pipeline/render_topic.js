// Render a topic's view as Markdown: ranked hits + relevance + summary links + citations.
// Usage: node --experimental-sqlite pipeline/render_topic.js <topicId>
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { open, ROOT } = require('./lib/db');

const STAT = { discovered: '⚪ 待取', pdf_downloaded: '📄 有全文', pdf_failed: '⛔ 取全文失败', summarized: '✅ 已总结' };

function main() {
  const topicId = process.argv[2];
  const db = open();
  const t = db.prepare('SELECT * FROM topics WHERE id=?').get(topicId);
  if (!t) { console.error('no such topic'); process.exit(1); }
  const rows = db.prepare(
    `SELECT p.*, pt.relevance, pt.relevance_reason, pt.rank
       FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
      WHERE pt.topic_id=? ORDER BY pt.rank`).all(topicId);

  // citation edges within this topic's set
  const ids = new Set(rows.map((r) => r.id));
  const edges = db.prepare('SELECT src_paper_id s, dst_paper_id d FROM citations').all()
    .filter((e) => ids.has(e.s) && ids.has(e.d));
  const titleById = new Map(rows.map((r) => [r.id, r.title]));
  db.close();

  const latestSummary = (r) => {
    const base = r.slug || r.id.replace(/[^a-z0-9._-]/gi, '_').slice(0, 180);
    const sv = path.join('store', 'summaries', base, 'v1.md');
    return fs.existsSync(path.join(ROOT, sv)) ? sv : null;
  };

  let md = `# 主题：${t.title}\n\n`;
  md += `> **研究思路**：${t.idea}\n\n`;
  md += `- 命中论文：${rows.length}　已总结：${rows.filter((r) => r.status === 'summarized').length}　最近更新：${(t.last_run_at || '').slice(0, 10)}\n`;
  md += `- 检索词：${JSON.parse(t.queries || '[]').map((q) => '`' + q + '`').join('、')}\n\n`;

  md += `## 命中清单（按相关性排序）\n\n`;
  md += `| # | 相关性 | 论文 | 年份 | 引用 | 状态 | 总结 |\n|--:|--:|---|--:|--:|---|---|\n`;
  for (const r of rows) {
    const s = latestSummary(r);
    const link = s ? `[v1](../../${s})` : '—';
    const edge = r.is_edge ? ' 🪨' : '';
    md += `| ${r.rank} | ${r.relevance ?? '-'} | ${(r.title || '').replace(/\|/g, '/')}${edge} | ${r.year || '-'} | ${r.citation_count || 0} | ${STAT[r.status] || r.status} | ${link} |\n`;
  }

  md += `\n_🪨 = 边角文章（低引用，保留以备不同视角）_\n\n`;

  md += `## 相关性理由\n\n`;
  for (const r of rows) md += `- **[${r.rank}] ${(r.title || '').slice(0, 70)}** （${r.relevance}）：${r.relevance_reason || ''}\n`;

  md += `\n## 库内引用关系（${edges.length} 条）\n\n`;
  if (edges.length === 0) md += `_暂无库内互相引用_\n`;
  else for (const e of edges)
    md += `- 《${(titleById.get(e.s) || '').slice(0, 45)}》→ 引用 →《${(titleById.get(e.d) || '').slice(0, 45)}》\n`;

  const out = path.join(ROOT, 'topics', topicId, 'topic.md');
  fs.writeFileSync(out, md);
  console.log(`rendered -> topics/${topicId}/topic.md  (${rows.length} papers, ${edges.length} citation edges)`);
}
main();
