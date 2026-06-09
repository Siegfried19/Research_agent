"""Record new summary versions produced by update_auto.py.
Usage: python3 pipeline/register_updates.py
"""
import json
import sys
from pathlib import Path

from lib.db import open_db, ROOT, now_iso


def main():
    wl = ROOT / "store" / "update_worklist.json"
    if not wl.exists():
        print("no update_worklist.json", file=sys.stderr)
        sys.exit(1)
    work = json.loads(wl.read_text(encoding="utf-8"))["work"]
    conn = open_db()
    n = missing = 0
    for w in work:
        out = Path(w["outPath"])  # prepare_update writes absolute paths
        if not out.exists() or out.stat().st_size < 100:
            missing += 1
            continue
        rel = str(out.relative_to(ROOT))
        based_on = json.dumps([r["id"] for r in (w.get("related") or [])], ensure_ascii=False)
        conn.execute(
            """INSERT OR IGNORE INTO summary_versions (paper_id,version,path,based_on,note,created_at)
               VALUES (?,?,?,?,?,?)""",
            (w["paperId"], w["nextVersion"], rel, based_on,
             f"基于 {len(w.get('related') or [])} 篇相关论文更新", now_iso()))
        conn.execute("UPDATE papers SET summarized_at=? WHERE id=?", (now_iso(), w["paperId"]))
        n += 1
    conn.commit()
    conn.close()
    print(f"registered {n} updated versions; {missing} missing output")


if __name__ == "__main__":
    main()
