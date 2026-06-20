"""统一失败分类器(2026-06-20)——不再靠关键词清单猜失败类型,让 `claude -p` 读报错判断。

缘由:旧 `_is_quota_err` 靠 ['usage limit','429','quota',...] 关键词匹配 codex 配额错;codex 换个
说法报错(如 `codex exec exit 1: ...` 不含这些词)就认不出 → escalate 走"全失败"分支 → daemon
误判成"坏PDF"发假警报(2026-06-19 那个 bug)。改成:一批失败去重后调一次 claude 判类别+恢复时长,
新报错格式也认得出,不用维护关键词。LLM 判断本身失败/解析失败 → 全部回退 unknown(=短重试,
fail toward retry,绝不 fail toward 假警报)。

类别 → 上层(escalate/daemon)据此决定睡多久/跳过单篇/报警:
- quota_exhausted   账户额度窗口用尽(小时级)         → 睡到恢复点(或长默认)
- transient         瞬时限流/抖动/超时/网络(分钟级)   → 短退避重试(daemon 递增 15→30→60)
- bad_input         PDF 读不了/损坏/缺失/无法解析     → 跳过**那一篇**(重试无用),不报警、不退整主题
- malformed_output  跑成功但输出空/非JSON             → 立即重试一次,仍旧则当 bad_input
- real_error        未登录/二进制缺失/配置错(要人修)  → 报警 + 停,别当坏PDF
- unknown           信息不足判不准                    → 保守按短重试处理
"""
import json
from datetime import datetime

from .claude import run_claude

CATEGORIES = ("quota_exhausted", "transient", "bad_input",
              "malformed_output", "real_error", "unknown")

# 批级聚合优先级:一批里出现的最高优先类别 = 这批整体怎么办。
# real_error 最先(要人) > quota(长睡) > transient/unknown(短睡重试) > malformed/bad_input(逐篇,非批级)。
_BATCH_PRIORITY = ("real_error", "quota_exhausted", "transient",
                   "unknown", "malformed_output", "bad_input")


def _prompt(errors, now_str):
    numbered = "\n".join(f"[{i}] {e}" for i, e in enumerate(errors))
    return f"""你是命令行 AI 工具(codex / claude -p)调用失败的**错误分类器**。下面每条是一次失败的报错文本。
现在时刻: {now_str}

把每条报错归入下列**恰好一个**类别,并估计需要等多久才值得重试(retry_minutes):
- quota_exhausted: 账户用量/额度窗口耗尽(小时级才恢复)。措辞如 usage limit reached、quota、you've hit your limit、try again at <时刻>/in <时长>。**若报错里给了恢复时刻或时长**,据"现在时刻"算出 retry_minutes;算不出填 120。
- transient: 瞬时限流/服务抖动/超时(timed out)/网络错/5xx/"please try again"——分钟级可恢复。retry_minutes 填 15。
- bad_input: 输入本身的问题——PDF 读不了/损坏/为空/缺失、文件不存在、内容无法解析。retry_minutes 填 null。
- malformed_output: 工具跑完了但输出空/不是要求的 JSON/格式畸形。retry_minutes 填 0。
- real_error: 真故障——未登录/认证过期、二进制找不到(not found)、参数/配置/权限错。retry_minutes 填 null。
- unknown: 信息不足、判不准。retry_minutes 填 15。

报错列表:
{numbered}

**只输出一个 JSON 数组**,每条报错对应一个对象(顺序按编号),不要解释、不要代码围栏:
[{{"i":0,"category":"...","retry_minutes":<整数或null>,"confidence":<0到1>}}]"""


def _extract_json_array(s):
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j < i:
        raise ValueError("no JSON array in output")
    return json.loads(s[i:j + 1])


def classify_failures(errors, timeout=120):
    """errors: 报错字符串列表(可含重复/空)。保序去重后**一次** claude 调用分类。
    返回 {error_str: {category, retry_minutes, confidence}}。
    任何环节失败(claude 挂/JSON 解析错)→ 全部回退 unknown(短重试),绝不抛。"""
    distinct = list(dict.fromkeys(e for e in errors if e))  # 保序去重,丢空串
    if not distinct:
        return {}
    fallback = {e: {"category": "unknown", "retry_minutes": 15, "confidence": 0.0}
                for e in distinct}
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        out = run_claude(_prompt(distinct, now_str), timeout=timeout)
        arr = _extract_json_array(out)
    except Exception:
        return fallback
    res = {}
    for obj in arr:
        try:
            i = obj.get("i")
            if not (isinstance(i, int) and 0 <= i < len(distinct)):
                continue
            cat = obj.get("category")
            res[distinct[i]] = {
                "category": cat if cat in CATEGORIES else "unknown",
                "retry_minutes": obj.get("retry_minutes"),
                "confidence": obj.get("confidence"),
            }
        except Exception:
            continue
    for e in distinct:           # 模型漏判的补 fallback
        res.setdefault(e, fallback[e])
    return res


def classify_batch(failed):
    """failed: [{"error":..}] 或 [str]。分类每条 + 聚合出**批级**裁决。
    返回 {category(批级最高优先类), retry_minutes(批级类下的值),
          categories(与 failed 对齐的逐条类别表), per_error(去重明细)}。"""
    errs = [((r.get("error") if isinstance(r, dict) else str(r)) or "") for r in failed]
    per = classify_failures(errs)
    cats = [per.get(e, {}).get("category", "unknown") for e in errs]
    batch_cat = "unknown"
    for c in _BATCH_PRIORITY:
        if c in cats:
            batch_cat = c
            break
    # 批级 retry_minutes:quota 取最大(最保守),其余取最小;都没有就 None。
    mins = [per[e]["retry_minutes"] for e in errs
            if per.get(e, {}).get("category") == batch_cat
            and isinstance(per.get(e, {}).get("retry_minutes"), (int, float))]
    if mins:
        retry = max(mins) if batch_cat == "quota_exhausted" else min(mins)
    else:
        retry = None
    return {"category": batch_cat, "retry_minutes": retry,
            "categories": cats, "per_error": per}
