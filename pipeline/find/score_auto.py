"""Automated relevance scoring: one `claude -p` call per batch of candidates.
Parses the JSON score array from stdout, writes scores/batch_<start>.json in the
format commit.py expects: [{id, relevance, reason, edge_insight, panel_objection?}].

Cross-model panel (config quality.codex_panel, default false): Codex reviews the
same batch as a devil's advocate (reject reasons only, no veto); objections ride
along in the batch files and are weighed at commit time.
Usage: python3 pipeline/find/score_auto.py <topicId> [batchSize] [concurrency]
"""
import json
import random
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT, load_config
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log

config = load_config()
log = get_logger("score")


# 主题无关的通用档位骨架(替代旧的、写死在 digital-human 主题上的例子)。
# 具体校准靠 anchor_block 注入的"已定分参照样本"——见 topic.json 的 score_anchors。
GENERIC_BANDS = """- 90-100: 直接命中研究思路的核心问题
- 60-89: 强相关(命中研究思路某个明确侧面,方法/任务高度对口)
- 30-59: 弱相关(沾边的 RL/方法/任务,但不针对研究思路要解决的问题)
- 0-29: 基本跑题(关键词撞上但实质无关)"""


def anchor_block(anchors):
    """把 topic.json 的 score_anchors 渲染成固定参照样本块,每批 prompt 一字不差地带,
    用来把所有批的打分刻度钉到同一把标尺(治跨批次校准漂移)。空则返回空串(冷启动裸跑)。"""
    if not anchors:
        return ""
    lines = "\n".join(f'- 「{(a.get("title") or "")[:90]}」→ {a["score"]} 分。{a.get("reason") or ""}'
                      for a in anchors)
    return (f"\n**已定分参照样本(把你的刻度对齐到这几篇,务必保持一致):**\n{lines}\n"
            "对每篇候选打分前,先想它相对这几个锚点该落在哪一档。\n")


def prompt(idea, batch, anchors=None):
    lst = "\n".join(
        f"- id: {c['id']}\n  title: {c['title']}\n  venue: {c.get('venue') or '(未知)'}\n"
        f"  abstract: {(c.get('abstract') or '(无摘要)')[:1200]}"
        for c in batch)
    return f"""你在为一个学术研究流水线做"相关性打分"。研究思路:

\"\"\"{idea}\"\"\"

下面是 {len(batch)} 篇候选论文。对每一篇,依据 title + abstract 判断它对上述研究思路的相关性,打 0-100 分:
{GENERIC_BANDS}
{anchor_block(anchors)}
另外判断 edge_insight: 若某篇相关性不高(<60)但提供了不寻常、可能启发新思路的视角,标 true。
**同时考虑来源质量**: 若标题/摘要明显是水刊/掠夺性期刊/低质量内容,即使主题相关也应压低分数。

候选论文:
{lst}

**只输出一个 JSON 数组**,不要任何解释、不要代码围栏。每篇一项,格式:
{{"id":"<原样照抄的 id>","relevance":<0-100整数>,"reason":"<一句话中文理由,必须引用 title/abstract 里的具体词句作为依据,不要泛泛而谈>","edge_insight":<true|false>}}"""


def panel_prompt(idea, batch):
    lst = "\n".join(
        f"- id: {c['id']}\n  title: {c['title']}\n  venue: {c.get('venue') or '(未知)'}\n"
        f"  abstract: {(c.get('abstract') or '(无摘要)')[:1200]}"
        for c in batch)
    return f"""You are the DEVIL'S ADVOCATE on a paper-screening panel for a curated research corpus.
The research idea (in Chinese):

\"\"\"{idea}\"\"\"

Below are {len(batch)} candidate papers. Your ONLY job is to find papers that should be
REJECTED from the corpus. For each paper, decide reject=true ONLY if you have a concrete,
specific reason, e.g.:
- clearly off-topic for the research idea above (despite keyword overlap)
- survey/review-mill or paper-mill smell: vague methodless abstract, buzzword stuffing
- predatory-journal style: grandiose claims, no concrete method or experiment
- abstract promises results but names no method, no data, no evaluation
Do NOT reject merely for being a preprint, low-cited, or narrow in scope.
If unsure, reject=false. Be strict but fair: typically 0-3 rejects per batch.

Candidates:
{lst}

Output ONLY a JSON array, no explanation, no code fences. One item per paper:
{{"id":"<id copied verbatim>","reject":<true|false>,"reason":"<one concise sentence in Chinese, empty if reject=false>"}}"""


def parse_scores(out):
    i, j = out.find("["), out.rfind("]")
    if i < 0 or j < 0 or j < i:
        raise ValueError("no JSON array in output")
    return json.loads(out[i:j + 1])


def boundary_rerank(score_dir, idea, anchors, allc, target, topic_id, band=8, k=5):
    """Scope (a): 只对"去留决策线"±band 分的窄带复称,治"漂移翻转去留"。把这十几篇塞进同一次调用
    (单一参照系)× k 次采样取均值(磨平生成抖动)。结果写 zz_boundary.json——文件名排在 batch_*.json
    之后,commit 的 sorted-glob 合并时按 id 覆盖,故无需改 commit.py。main() 开头已清空 scores/,幂等。

    决策线随首跑/增量不同(commit 选篇逻辑决定):
      - 首跑: 选 eligible[:target] → 去留线 = 第 target 名截断线(pool<target 时退回资格闸)。
      - 增量: 选 fresh[:target*3](cap 极少触顶) → 去留线 = 资格闸 rel>=30 / flag_min;已入库篇去留已定,跳过。"""
    merged = {}
    for f in sorted(score_dir.glob("batch_*.json")):
        for s in json.loads(f.read_text(encoding="utf-8")):
            merged[s["id"]] = s
    if len(merged) < 2:
        return
    ranked = sorted(merged.values(), key=lambda s: s["relevance"], reverse=True)
    from lib.db import open_db
    conn = open_db()
    existing = {r[0] for r in conn.execute(
        "SELECT paper_id FROM paper_topic WHERE topic_id=?", (topic_id,)).fetchall()}
    conn.close()
    flag_min = (config.get("quality") or {}).get("flag_min_relevance", 45)
    if not existing:  # 首跑
        centers = [ranked[target - 1]["relevance"]] if len(ranked) >= target else sorted({30, flag_min})
        mode = "first-run"
    else:             # 增量:去留线=资格闸;已入库篇不复称
        centers = sorted({30, flag_min})
        mode = "incremental"
    by_id = {c["id"]: c for c in allc}
    band_ids, seen = [], set()
    for s in ranked:
        if s["id"] in existing or s["id"] in seen:
            continue
        if any(c - band <= s["relevance"] <= c + band for c in centers):
            band_ids.append(s["id"])
            seen.add(s["id"])
    band_batch = [by_id[i] for i in band_ids if i in by_id]
    if len(band_batch) < 2:
        log.info(f"  boundary_rerank SKIP [{mode}]: 边界带仅 {len(band_batch)} 篇(centers={centers})")
        return
    log.info(f"  boundary_rerank [{mode}]: centers={centers} band=±{band} → {len(band_batch)} 篇复称 × {k} 次取均值")
    acc = {i: [] for i in band_ids}
    for _ in range(k):
        try:
            for s in parse_scores(run_claude(prompt(idea, band_batch, anchors))):
                if s["id"] in acc:
                    acc[s["id"]].append(int(float(s.get("relevance") or 0)))
        except Exception as e:  # noqa: BLE001  撞限流/解析失败:跳过该次采样,不中断整体
            log.info(f"  boundary_rerank sample skipped: {e}")
    out = [{**s, "relevance": round(sum(acc[s["id"]]) / len(acc[s["id"]])),
            "reason": f"{s.get('reason') or ''}[边界复称×{len(acc[s['id']])}→{round(sum(acc[s['id']]) / len(acc[s['id']]))}]"}
           for s in ranked if acc.get(s["id"])]
    if out:
        (score_dir / "zz_boundary.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"  boundary_rerank: {len(out)} 篇复称值写入 zz_boundary.json(commit 合并时覆盖)")


def autopick_anchors(score_dir, allc, topic_dir, topic_id, flag_min):
    """自举:从"裸跑整遍"的分布里自动挑 3 张样卷(高=最高分/边界=最接近资格闸/低=最低分),
    写进 topic.json.score_anchors,并非阻塞推 Telegram 告知(想改直接编辑 topic.json 后重跑 score)。
    标尺取自"整遍"而非第一批:候选池预排序过,第一批全是高相关、给不出低/边界样本。"""
    scores = {}
    for f in sorted(score_dir.glob("*.json")):
        for s in json.loads(f.read_text(encoding="utf-8")):
            scores[s["id"]] = s
    if len(scores) < 3:
        log.info(f"  autopick SKIP: 仅 {len(scores)} 篇打分,不足挑锚点")
        return []
    cand = {c["id"]: c for c in allc}
    ranked = sorted(scores.values(), key=lambda s: s["relevance"], reverse=True)
    boundary = min(scores.values(), key=lambda s: abs(s["relevance"] - flag_min))
    picks = []
    for taught, s in [(95, ranked[0]), (flag_min, boundary), (10, ranked[-1])]:
        c = cand.get(s["id"]) or {}
        picks.append({"title": c.get("title") or s["id"], "score": taught, "reason": s.get("reason") or ""})
    tj = topic_dir / "topic.json"
    o = json.loads(tj.read_text(encoding="utf-8"))
    o["score_anchors"] = picks
    tj.write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
    try:  # 非阻塞 FYI:告诉用户自举了哪些锚点,可事后改;不挡流程
        from lib.notify import notify
        notify(f"🎯 [{topic_id}] 自举打分锚点(全自动):\n" +
               "\n".join(f"  {p['score']}分: {p['title'][:60]}" for p in picks) +
               f"\n想改: 编辑 topics/{topic_id}/topic.json 的 score_anchors 后重跑 score")
    except Exception:  # noqa: BLE001
        pass
    return picks


def main():
    if len(sys.argv) < 2:
        print("usage: score_auto.py <topicId> [batchSize] [concurrency]", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    concurrency = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    topic_dir = ROOT / "topics" / topic_id
    cand = json.loads((topic_dir / "candidates.json").read_text(encoding="utf-8"))
    idea = cand["topic"]["idea"]
    allc = cand.get("candidates") or []
    target = cand.get("target") or config.get("first_run_target") or 100
    # 锚点直接读 topic.json(可能在 discover 之后才回填,candidates.json 里的 topic 拷贝未必有)
    anchors = []
    tj = topic_dir / "topic.json"
    if tj.exists():
        anchors = json.loads(tj.read_text(encoding="utf-8")).get("score_anchors") or []
    score_dir = topic_dir / "scores"
    score_dir.mkdir(parents=True, exist_ok=True)
    panel_on = bool((config.get("quality") or {}).get("codex_panel"))
    flag_min = (config.get("quality") or {}).get("flag_min_relevance", 45)

    def do_pass(pass_anchors, tag):
        """一整遍打分 over allc → 覆写 scores/batch_*.json(先清空)。返回 (scored, fail)。"""
        for f in score_dir.glob("*.json"):
            f.unlink()
        batches = [(s, allc[s:s + batch_size]) for s in range(0, len(allc), batch_size)]
        log.info(f"score_auto[{tag}]: {len(allc)} candidates in {len(batches)} batches (size {batch_size}), "
                 f"concurrency={concurrency}, anchors={len(pass_anchors)}, codex_panel={'ON' if panel_on else 'off'}")

        def worker(item, _i):
            start, batch = item
            b = list(batch)
            random.Random(start).shuffle(b)  # 批内洗牌对冲位置偏置;按 start 做种子保证幂等可复现
            arr = parse_scores(run_claude(prompt(idea, b, pass_anchors)))
            clean = [{"id": s["id"], "relevance": int(float(s.get("relevance") or 0)),
                      "reason": s.get("reason") or "", "edge_insight": bool(s.get("edge_insight"))} for s in arr]
            if panel_on:
                try:  # 评审团只提异议,失败不挡打分(panel 是补充层不是依赖)
                    from lib.codex import run_codex
                    objections = {o["id"]: o for o in parse_scores(run_codex(panel_prompt(idea, batch)))}
                    n_rej = 0
                    for s in clean:
                        o = objections.get(s["id"])
                        if o and o.get("reject"):
                            s["panel_objection"] = (o.get("reason") or "该拒(未给理由)")[:200]
                            n_rej += 1
                    log.info(f"  panel batch {start}: {n_rej} objections")
                except Exception as e:  # noqa: BLE001
                    log.info(f"  panel SKIP batch {start}: {e}")
            (score_dir / f"batch_{start}.json").write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info(f"  OK batch {start} ({len(clean)} scored)")
            return len(clean)

        res = pool(batches, worker, concurrency)
        return sum(r for r in res if isinstance(r, int)), sum(1 for r in res if not isinstance(r, int))

    # 无锚点 → 自举:先裸跑整遍(用通用骨架),从整遍分布自动挑3张样卷写回 topic.json,再带锚点重打一遍。
    # 标尺钉死后,后续增量复用冻好的锚点、不再自举。已有锚点(如手挑的 gt/dhi)直接单遍带锚跑。
    if not anchors:
        log.info("score_auto: 无 score_anchors → 自举(裸跑→挑样卷→带锚重打)")
        do_pass([], "bootstrap-bare")
        anchors = autopick_anchors(score_dir, allc, topic_dir, topic_id, flag_min)
        log.info(f"score_auto: 自举锚点 {[a['score'] for a in anchors]}")

    scored, fail = do_pass(anchors, "anchored" if anchors else "bare")
    log.info(f"score_auto done: {scored} scored, {fail} batches failed")
    boundary_rerank(score_dir, idea, anchors, allc, target, topic_id)
    run_log(topic_id, f"score_auto: {scored} scored, {fail} batches failed, anchors={len(anchors)}")


if __name__ == "__main__":
    main()
