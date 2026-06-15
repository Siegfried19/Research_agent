"""One-time migration: add slug column, backfill, rename files to title-based names,
fix DB paths. Idempotent (re-running after migration is a no-op).
Usage: python3 pipeline/tools/migrate_slugs.py
"""
import re
import shutil
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT
from lib.slug import unique_slug


def old_file_id(pid):
    return re.sub(r"[^a-z0-9._-]", "_", pid, flags=re.I)[:180]


def mv(a, b):
    a, b = Path(a), Path(b)
    if a.exists() and a != b:
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(a), str(b))
        return True
    return False


def main():
    conn = open_db()
    papers = conn.execute("SELECT id, title, slug, pdf_path, text_path FROM papers ORDER BY discovered_at").fetchall()
    renamed = slugged = 0
    for p in papers:
        slug = p["slug"] or unique_slug(conn, p["title"], p["id"])
        if not p["slug"]:
            conn.execute("UPDATE papers SET slug=? WHERE id=?", (slug, p["id"]))
            slugged += 1
        old = old_file_id(p["id"])
        if mv(ROOT / "store/pdfs" / (old + ".pdf"), ROOT / "store/pdfs" / (slug + ".pdf")):
            renamed += 1
        if mv(ROOT / "store/text" / (old + ".txt"), ROOT / "store/text" / (slug + ".txt")):
            renamed += 1
        if mv(ROOT / "store/summaries" / old, ROOT / "store/summaries" / slug):
            renamed += 1
        if p["pdf_path"]:
            conn.execute("UPDATE papers SET pdf_path=? WHERE id=?", (f"store/pdfs/{slug}.pdf", p["id"]))
        if p["text_path"]:
            conn.execute("UPDATE papers SET text_path=? WHERE id=?", (f"store/text/{slug}.txt", p["id"]))
        for sv in conn.execute("SELECT version, path FROM summary_versions WHERE paper_id=?", (p["id"],)).fetchall():
            fn = Path(sv["path"]).name
            conn.execute("UPDATE summary_versions SET path=? WHERE paper_id=? AND version=?",
                         (f"store/summaries/{slug}/{fn}", p["id"], sv["version"]))
    conn.commit()
    conn.close()
    print(f"migrated: {slugged} rows slugged, {renamed} files/dirs renamed")


if __name__ == "__main__":
    main()
