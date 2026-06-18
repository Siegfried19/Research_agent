"""Render a topic's view as Markdown: ranked hits + relevance + summary links + citations.
Usage: python3 pipeline/summarize/render_topic.py <topicId>
"""
import json
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT
from lib.slug import file_id

STAT = {"discovered": "⚪ 待取", "pdf_downloaded": "📄 有全文",
        "pdf_failed": "⛔ 取全文失败", "summarized": "✅ 已总结"}


def main():
    if len(sys.argv) < 2:
        print("usage: render_topic.py <topicId>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    conn = open_db()
    t = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
    if not t:
        print("no such topic", file=sys.stderr)
        sys.exit(1)
    rows = conn.execute(
        """SELECT p.*, pt.relevance, pt.relevance_reason, pt.rank
             FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
            WHERE pt.topic_id=? ORDER BY pt.rank""", (topic_id,)).fetchall()
    ids = {r["id"] for r in rows}
    edges = [(e["s"], e["d"]) for e in
             conn.execute("SELECT src_paper_id s, dst_paper_id d FROM citations").fetchall()
             if e["s"] in ids and e["d"] in ids]
    title_by_id = {r["id"]: r["title"] for r in rows}
    conn.close()

    def latest_summary(r):
        base = r["slug"] or file_id(r["id"])
        sv = f"store/summaries/{base}/v1.md"
        return sv if (ROOT / sv).exists() else None

    n_sum = sum(1 for r in rows if r["status"] == "summarized")
    queries = json.loads(t["queries"] or "[]")
    md = [f"# 主题：{t['title']}\n",
          f"> **研究思路**：{t['idea']}\n",
          f"- 命中论文：{len(rows)}　已总结：{n_sum}　最近更新：{(t['last_run_at'] or '')[:10]}",
          f"- 检索词：{'、'.join('`' + q + '`' for q in queries)}\n",
          "## 命中清单（按相关性排序）\n",
          "| # | 相关性 | 论文 | 年份 | 引用 | 状态 | 总结 |",
          "|--:|--:|---|--:|--:|---|---|"]
    suspects = [r for r in rows if r["quality_tier"] == "suspect"]
    for r in rows:
        s = latest_summary(r)
        link = f"[v1](../../{s})" if s else "—"
        edge = " 🪨" if r["is_edge"] else ""
        warn = " ⚠️" if r["quality_tier"] == "suspect" else ""
        title = (r["title"] or "").replace("|", "/")
        md.append(f"| {r['rank']} | {r['relevance'] if r['relevance'] is not None else '-'} | {title}{edge}{warn} | "
                  f"{r['year'] or '-'} | {r['citation_count'] or 0} | {STAT.get(r['status'], r['status'])} | {link} |")
    md.append("\n_🪨 = 边角文章（低引用，保留以备不同视角）"
              + ("　⚠️ = 来源可疑（掠夺刊名单命中，总结为质疑模式，引用前需独立验证）" if suspects else "") + "_\n")
    if suspects:
        md.append("## ⚠️ 低可信来源（带标记入库）\n")
        for r in suspects:
            md.append(f"- **[{r['rank']}] {(r['title'] or '')[:70]}**（{r['venue'] or '-'}；{r['quality_signals'] or ''}）"
                      f"——结论未经可信同行评审，仅作视角参考。")
        md.append("")
    md.append("## 相关性理由\n")
    for r in rows:
        md.append(f"- **[{r['rank']}] {(r['title'] or '')[:70]}** （{r['relevance']}）：{r['relevance_reason'] or ''}")
    md.append(f"\n## 库内引用关系（{len(edges)} 条）\n")
    if not edges:
        md.append("_暂无库内互相引用_")
    else:
        for s, d in edges:
            md.append(f"- 《{(title_by_id.get(s) or '')[:45]}》→ 引用 →《{(title_by_id.get(d) or '')[:45]}》")

    out = ROOT / "topics" / topic_id / "topic.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"rendered -> topics/{topic_id}/topic.md  ({len(rows)} papers, {len(edges)} citation edges)")


if __name__ == "__main__":
    main()
