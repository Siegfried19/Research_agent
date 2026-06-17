"""接地门:机械核对 note_plan 里每条的 quote_en 是否真在该篇 PDF 里(治张冠李戴)。

总结 agent 在写正文之前调它:`python3 pipeline/tools/grounding_gate.py <note_plan.json> <paper.pdf>`。
确定性、零 token——对 PDF 跑 pdftotext 抽全文,把两边都归一化成"连续字母数字串"
(去掉空白/连字符/标点,大小写无关),再判每条 quote_en 是不是子串。钉不住的逐条报出来,
agent 据此改 note_plan(找对引文/降 strength/标 [原文未提])再重跑,全过才许写正文。

退出码:全过=0,有钉不住的=1,note_plan 读不了/PDF 抽不出=2。
结果以 JSON 打到 stdout 供 agent 读;人看的小结打到 stderr。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

MIN_QUOTE_LEN = 12  # 归一化后短于此的引文不足以核对(太短易误中),判 too_short


def norm(s):
    """归一化成连续小写字母数字串:抹掉空白/连字符/标点,顺带吃掉 pdftotext 的断词换行
    (frame-\\nwork -> framework)和空格差异,使匹配对排版噪声鲁棒。"""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def pdf_text(pdf_path):
    tmp = Path(tempfile.gettempdir()) / f"gate_{_os.getpid()}.txt"
    try:
        subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", str(pdf_path), str(tmp)],
                       timeout=120, check=False)
        t = tmp.read_text(encoding="utf-8", errors="ignore")
        return t
    finally:
        tmp.unlink(missing_ok=True)


def check_one(quote, ntext):
    """返回 ok|partial|fail|too_short。partial=整段没中但前/后半段中了(轻微转写偏差),放行。"""
    nq = norm(quote)
    if len(nq) < MIN_QUOTE_LEN:
        return "too_short"
    if nq in ntext:
        return "ok"
    half = len(nq) // 2
    if nq[:half] in ntext or nq[half:] in ntext:
        return "partial"
    return "fail"


def main():
    if len(sys.argv) < 3:
        print("usage: grounding_gate.py <note_plan.json> <paper.pdf>", file=sys.stderr)
        sys.exit(2)
    plan_path, pdf_path = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if not isinstance(plan, list):
            raise ValueError("note_plan 顶层必须是 JSON 数组")
    except Exception as e:
        print(json.dumps({"error": f"读不了 note_plan: {e}"}, ensure_ascii=False))
        print(f"[gate] 读不了 note_plan: {e}", file=sys.stderr)
        sys.exit(2)

    raw = pdf_text(pdf_path)
    if len(raw.strip()) < 200:
        print(json.dumps({"error": f"pdftotext 抽不出文本: {pdf_path}"}, ensure_ascii=False))
        print(f"[gate] pdftotext 抽不出文本: {pdf_path}", file=sys.stderr)
        sys.exit(2)
    ntext = norm(raw)

    results, fails = [], []
    for i, e in enumerate(plan):
        q = (e or {}).get("quote_en", "")
        status = check_one(q, ntext)
        row = {"i": i, "status": status, "kind": (e or {}).get("kind"),
               "point": (e or {}).get("point", "")[:80], "where": (e or {}).get("where", ""),
               "quote_en": (q or "")[:120]}
        results.append(row)
        if status in ("fail", "too_short"):
            fails.append(row)

    all_pass = not fails
    print(json.dumps({"all_pass": all_pass, "n": len(plan), "n_fail": len(fails),
                      "fails": fails, "results": results}, ensure_ascii=False, indent=1))
    if all_pass:
        print(f"[gate] PASS — {len(plan)} 条引文全部钉得住", file=sys.stderr)
    else:
        print(f"[gate] FAIL — {len(fails)}/{len(plan)} 条钉不住,需修正:", file=sys.stderr)
        for r in fails:
            why = "引文太短无法核对" if r["status"] == "too_short" else "引文在 PDF 中找不到(疑似张冠李戴/编造出处)"
            print(f"  #{r['i']} [{r['status']}] {why} — {r['where']} | {r['quote_en']}", file=sys.stderr)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
