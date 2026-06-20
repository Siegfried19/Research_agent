"""Export a topic (or the whole library) as an ARS Material-Passport
`literature_corpus[]` YAML — the bridge from our library to the idea->paper
pipeline (总蓝图出口③). Schema: reference/academic-research-skills/shared/contracts/
passport/literature_corpus_entry.schema.json (v3.6.4 required fields + extras).

  python3 pipeline/tools/export_corpus.py <topicId|all> [--min-relevance N] [-o FILE]

Notes
- Entries without a year are REJECTED per schema (listed at the end), not coerced.
- quality_tier rides along as tags + user_notes warning (标记进库,出口必须认标记;
  ARS 侧的 bibliography_agent 自己还会再筛一轮 — Iron Rule 1: same criteria).
- source_pointer prefers the local PDF (file://), falls back to doi.org, then the
  summary dir. ARS never dereferences it; consumers fetch full text themselves.
- abstract/user_notes are PRIVATE fields (may contain copyrighted text) — the
  output file is for local ARS runs, don't publish it.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT
from lib.log import get_logger, run_log
from lib.store import paper_dir

log = get_logger("export_corpus")
ADAPTER = ("research-agent-sqlite", "1.0")


def csl_authors(raw):
    """Our authors are plain strings -> CSL-JSON names ({family,given} | {literal})."""
    out = []
    for a in json.loads(raw or "[]"):
        a = (a or "").strip()
        if not a:
            continue
        parts = a.split()
        if len(parts) >= 2:
            out.append({"family": parts[-1], "given": " ".join(parts[:-1])})
        else:
            out.append({"literal": a})
    return out


def citation_key(p, used):
    """bibtex 风格: <firstauthor-family><year><firstword>;保证唯一+符合 schema 字符集。"""
    try:
        first = json.loads(p["authors"] or "[]")[0].split()[-1]
    except Exception:
        first = "anon"
    word = next((w.lower() for w in re.findall(r"[A-Za-z]{3,}", p["title"] or "")
                 if w.lower() not in ("the", "and", "for", "with", "from")), "paper")
    base = re.sub(r"[^A-Za-z0-9_:-]", "", f"{first.lower()}{p['year']}{word}")
    if not re.match(r"^[A-Za-z]", base):
        base = "p" + base
    key, i = base, 2
    while key in used:
        key, i = f"{base}{i}", i + 1
    used.add(key)
    return key


def source_pointer(p):
    if p["pdf_path"] and (ROOT / p["pdf_path"]).exists():
        return f"file://{ROOT / p['pdf_path']}"
    if p["doi"]:
        return f"https://doi.org/{p['doi']}"
    return f"file://{paper_dir(p['slug'])}"


def arxiv_id(p):
    try:
        ax = json.loads(p["ext_ids"] or "{}").get("arxiv")
        if ax and re.match(r"^\d{4}\.\d{4,5}(v[1-9]\d*)?$", str(ax)):
            return str(ax)
    except Exception:
        pass
    return None


def venue_type(p):
    v = (p["venue"] or "").lower()
    if p["quality_tier"] == "flag" or "arxiv" in v:
        return "preprint"
    return "unknown"  # 不可靠就老实说 unknown(schema invariant: adapter-declared only)


def y(s):
    """YAML 标量:统一走 json.dumps(双引号转义),对 YAML 合法。"""
    return json.dumps(s, ensure_ascii=False)


def entry_yaml(e):
    lines = [f"  - citation_key: {y(e['citation_key'])}",
             f"    title: {y(e['title'])}",
             "    authors:"]
    for a in e["authors"]:
        if "literal" in a:
            lines.append(f"      - literal: {y(a['literal'])}")
        else:
            lines.append(f"      - family: {y(a['family'])}")
            lines.append(f"        given: {y(a['given'])}")
    lines.append(f"    year: {e['year']}")
    lines.append(f"    source_pointer: {y(e['source_pointer'])}")
    for k in ("venue", "doi", "arxiv_id", "venue_type", "obtained_via",
              "adapter_name", "adapter_version", "obtained_at", "abstract", "user_notes"):
        if e.get(k):
            lines.append(f"    {k}: {y(e[k])}")
    if e.get("tags"):
        lines.append("    tags:")
        lines += [f"      - {y(t)}" for t in e["tags"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--min-relevance", type=float, default=0)
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()
    conn = open_db()
    if a.topic == "all":
        rows = conn.execute(
            """SELECT p.*, GROUP_CONCAT(pt.topic_id) topic_ids, MAX(pt.relevance) relevance
                 FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                WHERE pt.relevance >= ? GROUP BY p.id ORDER BY relevance DESC""",
            (a.min_relevance,)).fetchall()
        out = ROOT / "storage" / "literature_corpus_all.yaml"
    else:
        rows = conn.execute(
            """SELECT p.*, pt.topic_id topic_ids, pt.relevance relevance
                 FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
                WHERE pt.topic_id=? AND pt.relevance >= ? ORDER BY pt.rank""",
            (a.topic, a.min_relevance)).fetchall()
        out = ROOT / "topics" / a.topic / "literature_corpus.yaml"
    if a.out:
        out = ROOT / a.out
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    used, entries, rejected = set(), [], []
    for p in rows:
        if not p["year"]:
            rejected.append((p["title"], "no year (schema requires integer year)"))
            continue
        authors = csl_authors(p["authors"])
        if not authors:
            rejected.append((p["title"], "no authors"))
            continue
        tier = p["quality_tier"] or "ok"
        notes = [f"relevance={p['relevance']:.0f}", f"quality_tier={tier}"]
        if tier == "suspect":
            notes.append("⚠️ 可疑来源(掠夺刊名单命中),引用前人工核实")
        elif tier == "flag":
            notes.append("预印本/未检出正式收录,未经同行评审确认")
        sdir = paper_dir(p["slug"] or "")
        vs = sorted(sdir.glob("v*.md")) if sdir.exists() else []
        if vs:
            notes.append(f"中文总结: {vs[-1]}")
        entries.append({
            "citation_key": citation_key(p, used), "title": p["title"],
            "authors": authors, "year": int(p["year"]),
            "source_pointer": source_pointer(p), "venue": p["venue"],
            "doi": p["doi"] if p["doi"] and re.match(r"^10\.\d{4,9}/\S+$", p["doi"]) else None,
            "arxiv_id": arxiv_id(p), "venue_type": venue_type(p),
            "obtained_via": "other", "adapter_name": ADAPTER[0],
            "adapter_version": ADAPTER[1], "obtained_at": now,
            "abstract": (p["abstract"] or None),
            "user_notes": "; ".join(notes),
            "tags": [f"topic:{t}" for t in str(p["topic_ids"]).split(",")] + [f"quality:{tier}"],
        })
    conn.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(entry_yaml(e) for e in entries)
    out.write_text(f"# ARS Material Passport literature_corpus — exported {now}\n"
                   f"# adapter: {ADAPTER[0]} v{ADAPTER[1]}  entries: {len(entries)}"
                   f"  rejected: {len(rejected)}\n"
                   f"# PRIVATE: contains abstracts/notes — for local ARS runs only.\n"
                   f"literature_corpus:\n{body}\n", encoding="utf-8")
    log.info(f"exported {len(entries)} entries -> {out.relative_to(ROOT)}")
    for t, why in rejected:
        log.info(f"  REJECTED [{why}] {(t or '')[:60]}")
    run_log(a.topic, f"export_corpus: {len(entries)} entries, {len(rejected)} rejected -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
