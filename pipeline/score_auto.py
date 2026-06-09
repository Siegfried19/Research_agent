"""Automated relevance scoring: one `claude -p` call per batch of candidates.
Parses the JSON score array from stdout, writes scores/batch_<start>.json in the
format commit.py expects: [{id, relevance, reason, edge_insight}].
Usage: python3 pipeline/score_auto.py <topicId> [batchSize] [concurrency]
"""
import json
import sys

from lib.db import ROOT
from lib.claude import run_claude, pool
from lib.log import get_logger, run_log

log = get_logger("score")


def prompt(idea, batch):
    lst = "\n".join(
        f"- id: {c['id']}\n  title: {c['title']}\n  abstract: {(c.get('abstract') or '(无摘要)')[:1200]}"
        for c in batch)
    return f"""你在为一个学术研究流水线做"相关性打分"。研究思路:

\"\"\"{idea}\"\"\"

下面是 {len(batch)} 篇候选论文。对每一篇,依据 title + abstract 判断它对上述研究思路的相关性,打 0-100 分:
- 90-100: 直接命中(用 RL/模仿学习训练数字人/虚拟人/具身智能体/仿真角色与环境交互、全身运动控制等)
- 60-89: 强相关(物理仿真角色动画、humanoid 控制、具身智能体决策等)
- 30-59: 弱相关(沾边的 RL/动画/机器人但不针对"数字人与环境交互")
- 0-29: 基本跑题(纯 VR 体验、metaverse 综述、质性研究方法等)

另外判断 edge_insight: 若某篇相关性不高(<60)但提供了不寻常、可能启发新思路的视角,标 true。
**同时考虑来源质量**: 若标题/摘要明显是水刊/掠夺性期刊/低质量内容,即使主题相关也应压低分数。

候选论文:
{lst}

**只输出一个 JSON 数组**,不要任何解释、不要代码围栏。每篇一项,格式:
{{"id":"<原样照抄的 id>","relevance":<0-100整数>,"reason":"<一句话中文理由>","edge_insight":<true|false>}}"""


def parse_scores(out):
    i, j = out.find("["), out.rfind("]")
    if i < 0 or j < 0 or j < i:
        raise ValueError("no JSON array in output")
    return json.loads(out[i:j + 1])


def main():
    if len(sys.argv) < 2:
        print("usage: score_auto.py <topicId> [batchSize] [concurrency]", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    concurrency = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    topic_dir = ROOT / "topics" / topic_id
    cand = json.loads((topic_dir / "candidates.json").read_text(encoding="utf-8"))
    idea = cand["topic"]["idea"]
    allc = cand.get("candidates") or []
    score_dir = topic_dir / "scores"
    score_dir.mkdir(parents=True, exist_ok=True)
    for f in score_dir.glob("*.json"):
        f.unlink()

    batches = [(s, allc[s:s + batch_size]) for s in range(0, len(allc), batch_size)]
    log.info(f"score_auto: {len(allc)} candidates in {len(batches)} batches (size {batch_size}), concurrency={concurrency}")

    def worker(item, _i):
        start, batch = item
        out = run_claude(prompt(idea, batch))
        arr = parse_scores(out)
        clean = [{"id": s["id"], "relevance": int(float(s.get("relevance") or 0)),
                  "reason": s.get("reason") or "", "edge_insight": bool(s.get("edge_insight"))} for s in arr]
        (score_dir / f"batch_{start}.json").write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"  OK batch {start} ({len(clean)} scored)")
        return len(clean)

    res = pool(batches, worker, concurrency)
    scored = sum(r for r in res if isinstance(r, int))
    fail = sum(1 for r in res if not isinstance(r, int))
    log.info(f"score_auto done: {scored} scored, {fail} batches failed")
    run_log(topic_id, f"score_auto: {scored} scored, {fail} batches failed")


if __name__ == "__main__":
    main()
