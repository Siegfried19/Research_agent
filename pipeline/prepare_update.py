"""Build an update worklist to re-summarize papers in light of related work.
Usage:
  python3 pipeline/prepare_update.py <paperId> [<paperId> ...]
  python3 pipeline/prepare_update.py --related <relId,relId> <paperId>
If no --related given, related papers default to summarized citation-neighbors.
"""
import json
import sys

from lib.db import open_db, ROOT


def latest_version(conn, pid):
    return conn.execute(
        "SELECT version, path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1",
        (pid,)).fetchone()


def citation_neighbors(conn, pid):
    out = set()
    for r in conn.execute("SELECT dst_paper_id x FROM citations WHERE src_paper_id=?", (pid,)).fetchall():
        out.add(r["x"])
    for r in conn.execute("SELECT src_paper_id x FROM citations WHERE dst_paper_id=?", (pid,)).fetchall():
        out.add(r["x"])
    return list(out)


def main():
    argv = sys.argv[1:]
    explicit_related = None
    ids = []
    i = 0
    while i < len(argv):
        if argv[i] == "--related":
            i += 1
            explicit_related = [s.strip() for s in argv[i].split(",") if s.strip()]
        else:
            ids.append(argv[i])
        i += 1
    if not ids:
        print("usage: prepare_update.py <paperId> [...] [--related id,id]", file=sys.stderr)
        sys.exit(1)

    conn = open_db()
    work = []
    for pid in ids:
        p = conn.execute("SELECT id, slug, title FROM papers WHERE id=?", (pid,)).fetchone()
        if not p:
            print(f"skip (not in db): {pid}")
            continue
        cur = latest_version(conn, pid)
        if not cur:
            print(f"skip (no existing summary): {pid}")
            continue
        rel_ids = [r for r in (explicit_related or citation_neighbors(conn, pid)) if r != pid
                   and conn.execute("SELECT 1 FROM papers WHERE id=? AND status='summarized'", (r,)).fetchone()]
        if not rel_ids:
            print(f"skip (no summarized related papers): {(p['title'] or '')[:40]}")
            continue
        related = []
        for r in rel_ids:
            rp = conn.execute("SELECT title FROM papers WHERE id=?", (r,)).fetchone()
            sv = conn.execute("SELECT path FROM summary_versions WHERE paper_id=? ORDER BY version DESC LIMIT 1",
                              (r,)).fetchone()
            if sv:
                related.append({"id": r, "title": rp["title"] if rp else None, "path": str(ROOT / sv["path"])})
        next_version = cur["version"] + 1
        out_path = ROOT / "store" / "summaries" / p["slug"] / f"v{next_version}.md"
        work.append({"paperId": pid, "title": p["title"], "currentVersion": cur["version"],
                     "currentPath": str(ROOT / cur["path"]), "nextVersion": next_version,
                     "outPath": str(out_path), "related": related})
    conn.close()

    out = ROOT / "store" / "update_worklist.json"
    out.write_text(json.dumps({"total": len(work), "work": work}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"update worklist: {len(work)} papers -> store/update_worklist.json")
    for w in work:
        print(f"  v{w['currentVersion']}->v{w['nextVersion']}  {len(w['related'])} related  {(w['title'] or '')[:45]}")


if __name__ == "__main__":
    main()
