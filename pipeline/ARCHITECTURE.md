# pipeline/ 架构地图

> 2026-06-18 把主链脚本从扁平的 `stages/` 改成**按流水线功能段分文件夹**(find/fetch/summarize/verify)。
> 理解这一页 = 看懂整条流水线。想跑流水线只需记住 **`run.py` + 11 个阶段名**，其余都是被调用的零件。
> ⚠️ **代码组织规范(2026-06-18 定,以后一律遵循)**:主链脚本**按功能段放进对应文件夹**,不再堆在一个目录。
> 加新主链脚本 = 放进它所属的段文件夹(find/fetch/summarize/verify),没有就新建一个段文件夹+`__init__.py`。

## 流水线 = 4 大阶段（先记这个）

11 个 stage 归纳成 4 步，逻辑链：**有什么 → 拿到全文 → 读懂写成中文 → 换个模型再校一遍**。

| 大步 | 含 stage | 一句话 |
|--:|---|---|
| **① 找论文** 🔍 | discover → score → commit | 多源搜 → claude 打分 → 选篇写库 |
| **② 取全文** 📥 | fetch → recover → hunt → tierb | 四级下载：OA → 规则兜底 → agent 猎源 → 付费墙；撞墙就固化新渠道 |
| **③ 写总结** ✍️ | worklist → sum → finalize | 建清单 → claude 直读 PDF 写 v1.md → 入库+渲染 topic.md |
| **④ 核查修正** ✅ | verify | Codex 跨模型全量查幻觉 → 修 major 出 vN+1（写的人≠查的人） |

> ⚠️ 别把 ②里的"四级下载"和这"4 大阶段"混为一谈——前者是取全文的 4 个兜底层级，后者是整条流水线的 4 个职能段。
> 下面那张表是同一结构的逐 stage 展开（脚本/引擎落点）。

## 目录布局

```
pipeline/
├─ run.py            ★唯一入口/总指挥。run auto = 按序调各段文件夹里 11 个阶段
├─ ask.py            ★出口①②公共 API(FTS5 检索)。全局 ~/.claude/CLAUDE.md 引它 → 路径不可动
├─ run.sh            run.py 的薄壳(bash 入口)
├─ remote_view.sh    tierb 远程看屏(已封存,默认关)
│
├─ find/        🔍 找论文  ← discover, score_auto, commit
├─ fetch/       📥 取全文  ← fetch_oa, recover_oa, recover_agent, fetch_tierb
├─ summarize/   ✍️ 写总结  ← build_worklist, summarize_auto, register_summaries, render_topic
├─ verify/      ✅ 核查    ← verify_summaries, escalate_verify
│   (上面 4 个段文件夹 = 主链 13 脚本,各有 __init__.py;只被 run.py 调用)
├─ tools/    ← 旁路 11 脚本。手动跑，永远不在 run auto 链上
└─ lib/      ← 共享工具箱。各段 + tools 都 import 它
```

## 主链段文件夹(run auto 的 11 阶段)

按执行顺序，分 4 个功能段文件夹（`run.py` 的 `AUTO` 列表 + `steps()` 表是唯一事实源）：

| 文件夹 | 阶段名(run.py) | 脚本 | 引擎 |
|---|---|---|---|
| **find/** 🔍找论文 | discover | `find/discover.py` | 纯代码(多源API) |
| | score | `find/score_auto.py` | claude -p 打分 |
| | commit | `find/commit.py` | 纯代码(选篇写库) |
| **fetch/** 📥取全文(四级) | fetch | `fetch/fetch_oa.py` | OA 直取 |
| | recover | `fetch/recover_oa.py` | 规则兜底 |
| | hunt | `fetch/recover_agent.py` | claude -p 联网猎 |
| | tierb | `fetch/fetch_tierb.py` | 浏览器+人工验证 |
| **summarize/** ✍️写总结 | worklist | `summarize/build_worklist.py` | 纯代码 |
| | sum | `summarize/summarize_auto.py` | claude -p 总结 |
| | finalize | `summarize/register_summaries.py` + `summarize/render_topic.py` | 纯代码 |
| **verify/** ✅核查修正 | verify | `verify/escalate_verify.py` → `summarize/render_topic.py` | Codex+claude |

verify 段两件套(2026-06-18 起)：`escalate_verify.py`(升级阶梯驱动) → `verify_summaries.py`(Codex 核查,report-only)；major 触发的"重做"**不在 verify 段**——是回到 summarize 段调 `summarize_auto.resummarize`(从 PDF 整篇重新总结出 vN+1,非打补丁)。旧 `correct_summaries.py`(在旧版上打补丁)已删,根治"反向裁决核查员+伪造核对背书"的 bug。
> ⚠️ **唯一的跨段 import**：`verify/escalate_verify.py` 用 `from summarize.summarize_auto import resummarize`(major 时回总结段整篇重做)。靠 path-shim 把 `pipeline/` 放进 `sys.path` + 各段有 `__init__.py` 才解析得到。改动这两个文件时留意。

## tools/ — 旁路(手动跑)

| 脚本 | 用途 |
|---|---|
| `export_corpus.py` | 出口③:导 ARS `literature_corpus` YAML |
| `bot.py` | Telegram 常驻对话 bot |
| `cross_topic.py` | 跨主题比较(需 ≥2 主题) |
| `audit_quality.py` | 回溯审计已入库论文(拉撤稿/DOAJ) |
| `suggest_updates`/`prepare_update`/`update_auto`/`register_updates` | 老总结增量更新链(一套) |
| `notify.py` | Telegram CLI |
| `init.py` | 建新主题脚手架 |
| `migrate_slugs.py` | 一次性迁移工具(历史遗留) |

## lib/ — 共享工具箱

`db`(库读写+配置) · `sources`(4个学术API) · `merge`(去重) · `quality`(硬信号质量) · `store`(PDF落盘校验) · `slug` · `http` · `log` · `notify` · **`claude`**(claude -p 引擎) · **`codex`**(codex 引擎)。
> 两个引擎是关键:`claude`(写东西) 和 `codex`(查东西)——"写的人和查的人不是同一个模型"在代码层的落点。

## import 机制(改文件前必读)

- `run.py` / `ask.py` 在根目录：`sys.path[0]` 自动是 `pipeline/`，`from lib.xxx` 直接通。
- 段文件夹(find/fetch/summarize/verify)/ `tools/` 里的脚本：顶部有 **path shim 三行**，把 `pipeline/` 插进 `sys.path`，让 `from lib.xxx` 解析到 `pipeline/lib`：
  ```python
  import os as _os, sys as _sys
  _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
  ```
- **同段 sibling import**(如 verify/ 内 `from verify_summaries import ...`)靠脚本自身目录在 `sys.path[0]` —— 同文件夹直接通。
- **跨段 import**(如 verify/ 用 summarize/ 的函数)走包路径 `from summarize.summarize_auto import ...` —— 靠 path-shim 把 `pipeline/` 入 `sys.path` + 段文件夹有 `__init__.py`。
- run.py 仍把每个阶段当**独立子进程** spawn(`subprocess.run([PY, "find/discover.py", ...], cwd=ROOT)`)，保留进程隔离 + cwd=仓库根(claude -p 按 cwd 读 CLAUDE.md)。

## 加新脚本怎么放

1. **进主链** → 放进它所属的**段文件夹**(find/fetch/summarize/verify);新功能段就新建文件夹+空 `__init__.py`。复制 path shim 三行，并在 `run.py` 的 `steps()` + `AUTO` 注册阶段名(路径写 `<段>/<脚本>.py`)。
2. **旁路工具** → 放 `tools/`，复制 path shim 三行。
3. **公共 API / 入口** → 才放根目录(像 ask.py)。⚠️ 根目录脚本路径若被外部(全局 CLAUDE.md / 别的项目)引用，不可随意搬。
