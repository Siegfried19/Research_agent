"""全天候 verify 排空守护进程(2026-06-18,用户定:codex 平时闲着,就让核查整天啃积压)。

循环:挑队列里还有"待核(已总结但没核到当前版本)"的最高优先主题 → 跑一批
`run.py <tid> verify`(已带 --max-papers 上限、最近的优先、撞配额会写 logs/codex_quota.json)→
  · 撞配额:解析"try again at X"睡到那个点自动醒来续(解不出睡默认窗口 ~5.5h),睡前发 Telegram;
  · 这批有进展:立刻接着下一批,把当前额度窗口吃满;
  · 这批没进展又没撞配额(剩下的多半是坏 PDF 等永久核不了的):跳过该主题,避免空转;
  · 全队列没待核了:发 Telegram"🎉 全部已核完"+ 自己退出;
  · 收到停止(kill / `touch logs/verify_daemon.stop`):发一声 + 退出。

吞吐天花板由 codex 配额定(此订阅一窗口 ~20 次、几小时级重置),daemon 只保证"窗口一开就用上"。
单例(pidfile)。不随开机自启——机器重启后手动再拉一次(同 bot.py)。
起:cd 仓库根 && setsid nohup python3 pipeline/tools/verify_daemon.py >> logs/verify_daemon.log 2>&1 &
停:kill $(cat logs/verify_daemon.pid)  或  touch logs/verify_daemon.stop
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.envguard import ensure_env
ensure_env()  # 不在 research-agent 环境就自动 re-exec 自己(同 run.py/ask.py)

from lib.db import ROOT, open_db
from lib.notify import notify
from lib.log import get_logger, run_log

log = get_logger("vdaemon")

PY = sys.executable
RUNPY = ROOT / "pipeline" / "run.py"
PIDFILE = ROOT / "logs" / "verify_daemon.pid"
STOPFLAG = ROOT / "logs" / "verify_daemon.stop"
QUOTA_STATE = ROOT / "logs" / "codex_quota.json"   # escalate/verify 写的失败信号,见 verify_summaries.write_signal
BATCH_PAUSE = 10  # 同一窗口内两批之间的小憩(秒),别贴着猛跑
# 退避策略(2026-06-20,失败类别由 lib/error_classify 的 LLM 判,daemon 据此睡多久):
TRANSIENT_BACKOFF = [15, 30, 60]   # 瞬时/unknown 类:递增退避(分钟)——连着撞就睡更久,别硬敲
QUOTA_DEFAULT_MIN = int(os.environ.get("VERIFY_QUOTA_DEFAULT_MIN", 120))  # 配额类没给恢复时刻时的默认睡眠(分)
MAX_NOPROGRESS = 2   # 无信号又无进展连续这么多次 → 跳过该主题(诚实"原因未明",不再断言"坏PDF")


def unverified_count(tid):
    """该主题已总结、还没核到当前版本、且没被钉版跳过(verify_skip)的篇数。"""
    conn = open_db()
    rows = conn.execute(
        """SELECT p.id AS id, MAX(sv.version) AS v FROM papers p
             JOIN paper_topic pt ON pt.paper_id=p.id
             JOIN summary_versions sv ON sv.paper_id=p.id
            WHERE pt.topic_id=? AND p.status='summarized'
            GROUP BY p.id""", (tid,)).fetchall()
    conn.close()

    def _load(name):
        try:
            return json.loads((ROOT / "topics" / tid / name).read_text(encoding="utf-8"))
        except Exception:
            return {}
    seen, skip = _load("verified.json"), _load("verify_skip.json")
    return sum(1 for r in rows
               if seen.get(r["id"]) != r["v"] and skip.get(r["id"], {}).get("version") != r["v"])


def topics_with_unverified(skip):
    """有待核篇的主题,按 priority 高在前、相同按建立序;排除本会话已判定空转的 skip。"""
    conn = open_db()
    tids = [r["id"] for r in conn.execute(
        "SELECT id FROM topics ORDER BY priority DESC, rowid ASC").fetchall()]
    conn.close()
    out = []
    for tid in tids:
        if tid in skip:
            continue
        n = unverified_count(tid)
        if n > 0:
            out.append((tid, n))
    return out


def stop_requested():
    return STOPFLAG.exists()


def sleep_interruptible(seconds):
    """睡 seconds,期间每 60s 看一次停止标记;被叫停返回 False。"""
    deadline = time.time() + max(0, seconds)
    while time.time() < deadline:
        if stop_requested():
            return False
        time.sleep(min(60, max(1, deadline - time.time())))
    return True


def read_quota_state():
    """读 escalate/verify 这批写的失败信号;返回 (hit, category, until_epoch_or_None)。读完即删。
    category ∈ quota_exhausted|transient|unknown|real_error(见 lib/error_classify);决定 daemon 怎么睡。"""
    if not QUOTA_STATE.exists():
        return False, None, None
    try:
        d = json.loads(QUOTA_STATE.read_text(encoding="utf-8"))
    except Exception:
        d = {"hit": True, "category": "unknown", "until": None}
    finally:
        QUOTA_STATE.unlink(missing_ok=True)
    until = None
    if d.get("until"):
        try:
            until = datetime.fromisoformat(d["until"]).timestamp()
        except Exception:
            until = None
    return bool(d.get("hit")), d.get("category", "unknown"), until


def acquire_singleton():
    if PIDFILE.exists():
        try:
            old = int(PIDFILE.read_text(encoding="utf-8").strip())
            os.kill(old, 0)
            print(f"verify_daemon 已在运行(pid={old}),拒绝重复启动", file=sys.stderr)
            sys.exit(1)
        except (ValueError, ProcessLookupError):
            pass  # 陈旧 pidfile,覆盖
        except PermissionError:
            print(f"verify_daemon 似已在运行(pid 存在),拒绝重复启动", file=sys.stderr)
            sys.exit(1)
    PIDFILE.write_text(str(os.getpid()), encoding="utf-8")


def run_one_batch(tid):
    """跑一批该主题的 verify(经 run.py,带 --max-papers 上限 + render + reindex)。返回 rc。"""
    return subprocess.run([PY, str(RUNPY), tid, "verify"], cwd=str(ROOT)).returncode


def main():
    STOPFLAG.unlink(missing_ok=True)  # 起新进程时清掉旧停止标记
    acquire_singleton()
    log.info("verify_daemon 启动:全天候排空核查积压")
    run_log("-", "verify_daemon start")
    notify("🟢 verify daemon 启动:开始全天候排空核查积压(撞配额会自动睡到窗口恢复;啃完自停)。")
    skip = set()       # 本会话判定核不动的主题(原因未明/真故障),不再重复挑
    transient_n = 0    # 连续瞬时退避计数(递增退避用:15→30→60)
    noprog = {}        # tid -> 连续"无信号无进展"次数
    try:
        while True:
            if stop_requested():
                notify("🛑 verify daemon 收到停止指令,已退出。")
                break
            cands = topics_with_unverified(skip)
            if not cands:
                if skip:
                    notify(f"✅ verify daemon:可核的都核完了,退出。另有 {len(skip)} 个主题"
                           f"剩余待核篇这轮核不动(原因未明/需人工:坏PDF或真故障?):{', '.join(sorted(skip))}")
                else:
                    notify("🎉 verify daemon:全队列总结已全部核完,退出。")
                log.info(f"queue drained (skip={sorted(skip)}) — exit")
                break

            tid, before = cands[0]
            log.info(f"挑中 {tid}(待核 {before}),跑一批 verify")
            QUOTA_STATE.unlink(missing_ok=True)  # 跑前清掉,这批撞 codex 侧问题才会重新写信号
            rc = run_one_batch(tid)
            hit, category, until = read_quota_state()

            if hit:
                # 失败类别(LLM 判)决定怎么睡——不再"十几分钟就硬敲"或误判坏PDF:
                if category == "real_error":
                    # 真故障(未登录/配置错):睡了没用,报警 + 跳过该主题,留给人。
                    log.info(f"{tid} 撞真故障(real_error)-> 报警 + 跳过该主题")
                    notify(f"🛑 verify daemon:{tid} 撞真故障(real_error,疑似未登录/配置错),"
                           f"跳过该主题待人工查。")
                    skip.add(tid)
                    if not sleep_interruptible(BATCH_PAUSE):
                        notify("🛑 verify daemon 收到停止指令,已退出。"); break
                    continue
                if category == "quota_exhausted":
                    transient_n = 0
                    secs = (until - time.time()) if (until and until > time.time()) else QUOTA_DEFAULT_MIN * 60
                    wake = datetime.fromtimestamp(time.time() + secs).strftime("%m-%d %H:%M")
                    log.info(f"{tid} codex 额度耗尽 -> 睡到 {wake}(~{int(secs/60)} 分)")
                    notify(f"⏸ verify daemon:codex 额度耗尽,睡到 {wake} 自动续核(进度已存)。")
                else:  # transient / unknown:递增短退避重试
                    mins = TRANSIENT_BACKOFF[min(transient_n, len(TRANSIENT_BACKOFF) - 1)]
                    transient_n += 1
                    secs = mins * 60
                    wake = datetime.fromtimestamp(time.time() + secs).strftime("%m-%d %H:%M")
                    log.info(f"{tid} codex 瞬时不稳({category})-> 睡 {mins} 分(第 {transient_n} 次)再重试")
                    notify(f"⏸ verify daemon:codex 瞬时不稳({category}),睡 {mins} 分后自动重试(进度已存)。")
                if not sleep_interruptible(secs):
                    notify("🛑 verify daemon 睡眠中收到停止指令,已退出。")
                    break
                continue  # 醒来重挑(可能夜间又多了新总结)

            # 没撞 codex 侧问题:正常推进。瞬时计数清零。
            transient_n = 0
            after = unverified_count(tid)
            if after < before:
                noprog[tid] = 0
                log.info(f"{tid} 待核 {before}->{after},继续吃当前窗口")
            else:
                # 无信号又无进展:本批可核的多半已被钉版跳过(bad_input/malformed,unverified_count 已扣),
                # 仍不降 = 剩的暂时推不动。连续 MAX_NOPROGRESS 次才跳过该主题,且话说诚实(不断言坏PDF)。
                noprog[tid] = noprog.get(tid, 0) + 1
                log.info(f"{tid} 本批无进展(rc={rc},{before}->{after}),第 {noprog[tid]}/{MAX_NOPROGRESS} 次")
                if noprog[tid] >= MAX_NOPROGRESS:
                    log.info(f"{tid} 连续无进展 -> 跳过该主题(原因未明,待人工)")
                    skip.add(tid)
            if not sleep_interruptible(BATCH_PAUSE):
                notify("🛑 verify daemon 收到停止指令,已退出。")
                break
    finally:
        run_log("-", "verify_daemon stop")
        PIDFILE.unlink(missing_ok=True)
        STOPFLAG.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
