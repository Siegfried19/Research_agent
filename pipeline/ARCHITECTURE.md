# pipeline/ 架构地图

> 2026-06-15 把扁平的 27 个脚本按职责分了文件夹。理解这一页 = 看懂整条流水线。
> 想跑流水线只需记住 **`run.py` + 11 个阶段名**，其余都是被调用的零件。

## 目录布局

```
pipeline/
├─ run.py            ★唯一入口/总指挥。run auto = 按序调 stages/ 里 11 个阶段
├─ ask.py            ★出口①②公共 API(FTS5 检索)。全局 ~/.claude/CLAUDE.md 引它 → 路径不可动
├─ run.sh            run.py 的薄壳(bash 入口)
├─ remote_view.sh    tierb 远程看屏(已封存,默认关)
│
├─ stages/   ← 主链 14 脚本。只被 run.py 调用，不要手动 mv 出去
├─ tools/    ← 旁路 11 脚本。手动跑，永远不在 run auto 链上
└─ lib/      ← 共享工具箱。stages/tools 都 import 它
```

## stages/ — 主链(run auto 的 11 阶段)

按执行顺序，分 4 个职能段（`run.py` 的 `AUTO` 列表 + `steps()` 表是唯一事实源）：

| 段 | 阶段名(run.py) | 脚本 | 引擎 |
|---|---|---|---|
| 🔍找论文 | discover | `discover.py` | 纯代码(多源API) |
| | score | `score_auto.py` | claude -p 打分 |
| | commit | `commit.py` | 纯代码(选篇写库) |
| 📥取全文(四级) | fetch | `fetch_oa.py` | OA 直取 |
| | recover | `recover_oa.py` | 规则兜底 |
| | hunt | `recover_agent.py` | claude -p 联网猎 |
| | tierb | `fetch_tierb.py` | 浏览器+人工验证 |
| ✍️写总结 | worklist | `build_worklist.py` | 纯代码 |
| | sum | `summarize_auto.py` | claude -p 总结 |
| | finalize | `register_summaries.py` + `render_topic.py` | 纯代码 |
| ✅核查修正 | verify | `escalate_verify.py` → `render_topic.py` | Codex+claude |

verify 阶段内部三件套：`escalate_verify.py`(升级阶梯驱动) → `verify_summaries.py`(Codex 核查) → `correct_summaries.py`(claude 修正出 vN+1)。这三个 + `summarize_auto` 之间有 sibling import，所以**必须同在 stages/**。

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
- `stages/` `tools/` 里的脚本：顶部有 **path shim 三行**，把 `pipeline/` 插进 `sys.path`，让 `from lib.xxx` 解析到 `pipeline/lib`：
  ```python
  import os as _os, sys as _sys
  _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
  ```
- sibling import(如 `from summarize_auto import full_text`)靠脚本自身目录在 `sys.path[0]` —— 所以互相 import 的脚本要放同一文件夹。

## 加新脚本怎么放

1. **进主链** → 放 `stages/`，复制 path shim 三行，并在 `run.py` 的 `steps()` + `AUTO` 注册阶段名。
2. **旁路工具** → 放 `tools/`，复制 path shim 三行。
3. **公共 API / 入口** → 才放根目录(像 ask.py)。⚠️ 根目录脚本路径若被外部(全局 CLAUDE.md / 别的项目)引用，不可随意搬。
