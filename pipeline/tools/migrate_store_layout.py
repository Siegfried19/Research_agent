"""One-time migration: 把每篇论文的 PDF + 总结归并到 store/papers/<slug>/ 一个家。

OLD(现状,散在两处):
  store/pdfs/<slug>.pdf              ← PDF
  store/summaries/<slug>/v*.md       ← 总结各版本
NEW(归并后):
  store/papers/<slug>/paper.pdf
  store/papers/<slug>/v*.md

同时改写 DB 路径列:papers.pdf_path、summary_versions.path。

【明确不做】不碰 verify 任何东西:topics/*/verified.json|verify_status.json|verify_skip.json、
daemon、续核逻辑全部原样不动。codex 判断文字"落进论文文件夹"是另一件事——由 verify 代码
往后跑时顺手写 store/papers/<slug>/verify.json(本脚本不负责,见交接说明)。

用法:
  python3 pipeline/tools/migrate_store_layout.py            # dry-run(默认):打印计划,什么都不动
  python3 pipeline/tools/migrate_store_layout.py --apply    # 真搬文件 + 改 DB
幂等:--apply 跑过后再跑是 no-op(源已不在、目标已在 → 自动跳过)。
安全:动手前先整盘备份(尤其 db/papers.sqlite);想先试可拷一份项目 + RESEARCH_DB=/tmp/x.sqlite 跑 --apply。
"""
import json
import re
import shutil
import sys
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT

APPLY = "--apply" in sys.argv


def main():
    mode = "APPLY(真改盘+改库)" if APPLY else "DRY-RUN(只看不改)"
    print(f"=== migrate_store_layout — {mode} ===")
    print(f"ROOT={ROOT}\n")

    conn = open_db()
    papers = conn.execute("SELECT id, slug, pdf_path FROM papers ORDER BY discovered_at").fetchall()

    n_dir = n_pdf = n_md = n_skip_done = 0
    db_updates = []   # (pid, version|None, newpath);version=None 表示 papers.pdf_path

    for p in papers:
        slug = p["slug"]
        if not slug:
            continue
        old_pdf = ROOT / "store" / "pdfs" / f"{slug}.pdf"
        old_sumdir = ROOT / "store" / "summaries" / slug
        newdir = ROOT / "store" / "papers" / slug

        sum_files = sorted(old_sumdir.iterdir()) if old_sumdir.exists() else []
        has_pdf = old_pdf.exists()
        if not (has_pdf or sum_files):
            # 已搬过的:目标在、源不在 → 仍纠正一次 DB(幂等),但不计入"涉及"
            if (newdir / "paper.pdf").exists():
                db_updates.append((p["id"], None, f"store/papers/{slug}/paper.pdf"))
            for f in (newdir.glob("v*.md") if newdir.exists() else []):
                m = re.fullmatch(r"v(\d+)\.md", f.name)
                if m:
                    db_updates.append((p["id"], int(m.group(1)), f"store/papers/{slug}/{f.name}"))
            if (newdir / "paper.pdf").exists() or (newdir.exists() and any(newdir.glob("v*.md"))):
                n_skip_done += 1
            continue

        actions = []

        # --- PDF ---
        if has_pdf:
            dst = newdir / "paper.pdf"
            actions.append(f"mv  {old_pdf.relative_to(ROOT)}  ->  {dst.relative_to(ROOT)}")
            if APPLY:
                newdir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_pdf), str(dst))
            n_pdf += 1
            db_updates.append((p["id"], None, f"store/papers/{slug}/paper.pdf"))

        # --- 总结各版本(.md 及任何残留文件)---
        for f in sum_files:
            dst = newdir / f.name
            actions.append(f"mv  {f.relative_to(ROOT)}  ->  {dst.relative_to(ROOT)}")
            if APPLY:
                newdir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dst))
            n_md += 1
            m = re.fullmatch(r"v(\d+)\.md", f.name)   # 只有 vN.md 对应 summary_versions 行
            if m:
                db_updates.append((p["id"], int(m.group(1)), f"store/papers/{slug}/{f.name}"))
        if APPLY and old_sumdir.exists() and not any(old_sumdir.iterdir()):
            old_sumdir.rmdir()   # 搬空后删掉旧空目录

        n_dir += 1
        print(f"[{slug}]")
        for a in actions:
            print(f"    {a}")

    # 改 DB 路径
    if APPLY:
        for pid, ver, path in db_updates:
            if ver is None:
                conn.execute("UPDATE papers SET pdf_path=? WHERE id=?", (path, pid))
            else:
                conn.execute("UPDATE summary_versions SET path=? WHERE paper_id=? AND version=?",
                             (path, pid, ver))
        conn.commit()
    conn.close()

    print("\n=== 计划小结 ===")
    print(f"  涉及论文文件夹: {n_dir}   (另有 {n_skip_done} 篇已是新布局,跳过)")
    print(f"  搬 PDF: {n_pdf}   搬总结文件: {n_md}")
    print(f"  待改 DB 路径行: {len(db_updates)}  (papers.pdf_path + summary_versions.path)")
    print("\n  注:本脚本只搬 PDF+总结、改 DB,**不碰 verify**。")
    if not APPLY:
        print("  以上为 dry-run。确认无误后加 --apply 真执行(先备份!)。")


if __name__ == "__main__":
    main()
