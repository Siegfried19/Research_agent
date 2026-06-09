"""Human-readable filename slug from a paper title (keeps latin + CJK/kana).

The canonical paper key stays the normalized DOI; slug is only for file naming.
"""
import re
import unicodedata

# keep ascii letters/digits, CJK unified, hiragana, katakana; else -> space
_KEEP = re.compile(r"[^0-9A-Za-z぀-ヿ一-鿿]+")


def slugify(title):
    s = unicodedata.normalize("NFKC", title or "").strip()
    s = _KEEP.sub(" ", s).strip()
    s = re.sub(r"\s+", "_", s)
    if len(s) > 90:
        s = re.sub(r"_+[^_]*$", "", s[:90])  # trim partial trailing word
    s = s.strip("_")
    return s or "untitled"


def unique_slug(conn, title, paper_id):
    """Ensure the slug is unique within papers.slug (excluding the same id)."""
    base = slugify(title)
    cand, n = base, 1
    while conn.execute("SELECT id FROM papers WHERE slug=? AND id<>?", (cand, paper_id)).fetchone():
        n += 1
        cand = f"{base}_{n}"
    return cand
