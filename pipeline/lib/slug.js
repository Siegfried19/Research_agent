// Human-readable filename slug from a paper title (keeps latin + CJK/kana).
// The canonical paper key stays the normalized DOI; slug is only for file naming.
'use strict';

function slugify(title) {
  let s = (title || '').normalize('NFKC').trim();
  // keep letters, digits, CJK, hiragana, katakana; everything else -> space
  s = s.replace(/[^\p{L}\p{N}぀-ヿ一-鿿]+/gu, ' ');
  s = s.trim().replace(/\s+/g, '_');
  if (s.length > 90) s = s.slice(0, 90).replace(/_+[^_]*$/, ''); // trim partial trailing word
  s = s.replace(/^_+|_+$/g, '');
  return s || 'untitled';
}

// Ensure the slug is unique within papers.slug (excluding the same id).
function uniqueSlug(db, title, id) {
  const base = slugify(title);
  let cand = base, n = 1;
  const stmt = db.prepare('SELECT id FROM papers WHERE slug=? AND id<>?');
  while (true) {
    const row = stmt.get(cand, id);
    if (!row) return cand;
    n += 1;
    cand = `${base}_${n}`;
  }
}

module.exports = { slugify, uniqueSlug };
