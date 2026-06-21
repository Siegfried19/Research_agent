"""Launcher: raise ONE orchestrator Claude to drive the whole `find` stage for a topic.

Replaces the hard-wired discover->score->commit chain with a single Claude that is
given the tools + current situation + project contract + notification rules, and full
discretion over HOW to search / fan out / branch / how many to keep per facet.
See find-facet-rewrite-design.md §3 (编排) and §5 (prompt).

python only "raises + wraps up"; the orchestrator calls discover/seed/score/commit as
Bash tools. cron and chat share this same path — only the trigger and --notify differ.

Usage: python3 pipeline/find/drive.py <topicId> [--notify] [--timeout SECONDS] [--dry-run]
"""
import sys

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import ROOT, open_db
from lib import topic as T
from lib.claude import run_claude
from lib.log import get_logger, run_log

log = get_logger("drive")

# headless 无权限弹窗:不在表里的工具一律被拒,所以这里就是 orchestrator 的全部能力面
ORCH_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Task", "WebSearch", "WebFetch"]

PROMPT_TEMPLATE = """你在为研究主题「__TOPIC_ID__」做文献「发现」(find):把一段研究思路 + 检索词,变成"哪些论文进这个主题"。只决定选篇并写库,不取全文、不写总结(那是后面 fetch/summarize 的事)。你全程自己判断怎么干,跑完给我一个简短回报。

【当前情况】
- 意图存档 topics/__TOPIC_ID__/topic.json(自己 Read 它),字段含义:
  · idea=全局总思路;target=目标总篇数;preferences=全局取舍偏好。
  · facets[]=主题的子方向,每个带:key/title、hit_criteria(这个 facet 的命中标准=你判相关的尺子)、queries(该方向检索词)、anchors(已定分参照样本,把打分刻度对齐到它们)、seed_ids(必须收进来的奠基作,按 id 播种)、note(软偏好)。无 facets=当单一主题处理。
- 状态存档 topics/__TOPIC_ID__/topic_state.json(自己 Read):各 facet 覆盖/已入库数、turning_seeds(上轮留的拐弯线索,可作本轮起点)。
- 库现状(我给你)：
__SITUATION__

【你的工具(Bash 调,输出 JSON/日志,你读了再决定下一步)】
- python3 pipeline/find/discover.py topics/__TOPIC_ID__/topic.json [--facet <key>]
    → 按 queries 四源召回去重成候选池(写 topics/__TOPIC_ID__/candidates.json,不写库)。
      不带 --facet=按全部 facet 的词搜一遍、每条候选自动打 facet 标签;带 --facet=只搜该 facet 并并入已有池。
- python3 pipeline/find/seed.py __TOPIC_ID__ <id...>
    → 按 DOI/arxiv id 把指定奠基作直接拉元数据入候选池(绕过关键词检索+截断),标 seeded。stdout 打 JSON 摘要。
- python3 pipeline/find/score_auto.py __TOPIC_ID__
    → 对候选逐批打相关性分(faceted 时每 facet 用自己的 anchors+hit_criteria,锚点校准)。
- python3 pipeline/find/commit.py topics/__TOPIC_ID__ --plan
    → 不写库,按 facet 摆出分布(每 facet eligible/fresh/分档桶/逐篇 id+rel+质量)给你看,据此决定每组留几篇。
- python3 pipeline/find/commit.py topics/__TOPIC_ID__ --keep <facet>=<N>,<facet2>=<M>   (或 --keep all)
    → 按你的决定把每个 facet 的 top-N eligible 写库。不带 --plan/--keep = auto(老式全局选,兜底用)。
- Read / Write → 读写两个存档(你可更新 queries/turning_seeds/coverage)。
- Task → 放手开子 agent(facet 是独立搜索线,鼓励一个 facet 一个子 agent 各搜各的、各回小总结:找到啥/覆盖够不够/候选/拐弯线索)。
- python3 pipeline/tools/notify_cli.py "消息" → 给用户发 Telegram。

【⚠️ 无头运行——最重要的一条】
你是 claude -p 无头模式,**没有"挂后台等唤醒(background + wake me later)"这回事**:你一旦停止调用工具、结束发言,整个 find 进程立刻就结束了,没人会再唤醒你。所以:
- 每一步都**前台同步跑**——调一个工具就等它真正返回、读到结果,再决定下一步。**绝不要**用 `&` / nohup / run_in_background 把 score_auto 之类挂后台然后停下。
- score_auto 打分耗时几分钟(嵌套 claude),**就等它整段跑完**,这是正常的,别因为"慢"就挂后台。
- 一口气把 discover →(按需 seed 播种)→ score_auto → commit --plan → commit --keep 全程走完,**再**回报。只有 commit 写库了这次 find 才算数。

【怎么干——你自己判断】
拆/搜/开几个子 agent/拐几轮/每个 facet 留几篇,全凭你判断。覆盖够了就停。preferences 和各 facet 的 note 要认。
典型流程(不是死路书,可偏离):看情况→discover(+按需 seed_ids 播种)→score_auto→commit --plan 看分布→commit --keep 定稿。
⭐ 收进论文后,翻它们的引用:被反复引、却没在候选池里的奠基作,用 seed.py 按 id 播种捞回来——关键词检索常漏这种,这是兜底主力。

【项目契约(你必须遵守,这些不是你能凭空知道的)】
- 选篇靠你的相关性判断,不靠 API 引用量排序(高引常跑题)。
- 文件名用 slug 不用 DOI;papers.id 是 TEXT 主键(无 DOI 没关系)。
- 质量"标记进库、出口认标记":block 永不入库,flag/suspect 带标记入库需更相关(commit 已内置该闸)。
- 幂等可重跑(已做的跳过);别 git push(只 commit 由用户 push)。
- 撞限流就重跑该步;并发别开太猛刷崩学校访问。
- 测试用临时库:别动生产库时设 RESEARCH_DB=/tmp/x.sqlite。本次是真跑,用默认生产库。

【通知规则】
跑完给我一个简短回报(commit 了啥/各 facet 留了几篇/有无遗留)。撞到"新发现"主动 notify 我:① 想加存档里没有的 facet;② 拐弯线索指向一个新子领域;③ 某 facet 怎么都喂不饱。默认你继续跑,通知只是让我能叫停/改向,不必等我。

开始吧。"""


def build_situation(topic_id):
    topic = T.load_topic(topic_id)
    state = T.load_state(topic_id)
    conn = open_db()
    n_db = conn.execute("SELECT COUNT(*) FROM paper_topic WHERE topic_id=?", (topic_id,)).fetchone()[0]
    conn.close()
    mode = "增量(每周追新,据此别重收已入库的)" if n_db > 0 else "冷启动(库空,力度可大)"
    lines = [f"  该主题已入库 {n_db} 篇 → {mode}。",
             f"  facets({len(topic['facets'])}){'  [topic.json 无 facets,当单一主题]' if not topic['_faceted'] else ''}:"]
    for f in topic["facets"]:
        fs = state["facets"].get(f["key"], {})
        lines.append(f"    · {f['key']}: {f['title']}  | queries {len(f['queries'])} / seed_ids {len(f['seed_ids'])}"
                     f" / anchors {len(f['anchors'])} | 库内 {fs.get('in_db', '?')} 覆盖 {fs.get('coverage', '?')}")
    lines.append(f"  turning_seeds: {len(state['turning_seeds'])} 条(起点线索,详见 topic_state.json)")
    return "\n".join(lines), topic, n_db


def build_prompt(topic_id):
    situation, _, _ = build_situation(topic_id)
    return (PROMPT_TEMPLATE
            .replace("__TOPIC_ID__", topic_id)
            .replace("__SITUATION__", situation))


def main():
    args = sys.argv[1:]
    do_notify = "--notify" in args
    if do_notify:
        args.remove("--notify")
    dry = "--dry-run" in args
    if dry:
        args.remove("--dry-run")
    timeout = 1800
    if "--timeout" in args:
        i = args.index("--timeout")
        timeout = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print("usage: drive.py <topicId> [--notify] [--timeout SECONDS] [--dry-run]", file=sys.stderr)
        sys.exit(1)
    topic_id = args[0]

    _os.chdir(ROOT)  # orchestrator 的 Bash 从仓库根跑
    prompt = build_prompt(topic_id)
    if dry:
        print(prompt)
        return

    log.info(f"# drive: raising orchestrator for '{topic_id}' (timeout {timeout}s, tools {ORCH_TOOLS})")
    run_log(topic_id, f"drive: orchestrator start (timeout={timeout})")
    if do_notify:
        try:
            from lib.notify import notify
            notify(f"🔎 find orchestrator 起跑: {topic_id}")
        except Exception:  # noqa: BLE001
            pass
    out = run_claude(prompt, model="opus", timeout=timeout, tools=ORCH_TOOLS)
    print(out)
    run_log(topic_id, "drive: orchestrator done")
    if do_notify:
        try:
            from lib.notify import notify
            notify(f"✅ find orchestrator 收工: {topic_id}\n{out[:1500]}")
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    main()
