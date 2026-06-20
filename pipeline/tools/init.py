"""Phase 0: create directory structure + initialize the SQLite database.
Usage: python3 pipeline/tools/init.py
"""
# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT, DB_PATH

DIRS = ["data-base", "storage/papers", "storage/dl_tmp", "topics", "logs"]


def main():
    for d in DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    conn = open_db()
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    conn.close()
    print("Initialized research pipeline.")
    print("  root :", ROOT)
    print("  db   :", DB_PATH)
    print("  dirs :", ", ".join(DIRS))
    print("  tables:", ", ".join(tables))


if __name__ == "__main__":
    main()
