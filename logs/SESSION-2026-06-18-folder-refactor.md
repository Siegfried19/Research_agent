# SESSION 2026-06-18 — 主链脚本按功能段分文件夹(重构)

> 换新机器后第一次正式干活。用户要"先把框架处理清楚,从第一层(找论文)开始",讨论后落到一次代码组织重构。
> 提交:`c93bb51 refactor(pipeline): 主链脚本按功能段分文件夹(find/fetch/summarize/verify)`

## 一、起因
- 用户觉得 `pipeline/stages/` 一个文件夹堆 14 个主链脚本**难维护**(改"找论文"要在 14 个里翻出 3 个;心里装不下全貌)。
- 明确意图:**按功能分文件夹**,文件还是一个个分开(不合并成一个文件),"可以不用做成包,但最好要文件夹"。
- 用户担心:中间很多脚本调 agent(claude/codex),打包/挪动会不会出问题。

## 二、关键判断(讨论后)
- **agent 调用不受影响**:`lib/claude.py`/`lib/codex.py` 是**跨进程**调外部 CLI(`shutil.which` 找 + prompt 走 stdin + 结果走 stdout),与 Python 文件夹/import 结构无关。
- 真正要小心的只有两点(已处理):① run.py 里写死的 13 处调度路径要跟着改;② 保持 `cwd=仓库根`(claude -p 按 cwd 读 CLAUDE.md)。
- 脚本间耦合摸查结果:**唯一跨段 import = `verify_summaries.py` → `from summarize_auto import full_text`**;verify 三件套互引都同段。外部(全局 ~/.claude/CLAUDE.md)**没有**引用 stages/ 路径。

## 三、做了什么
主链 14 脚本 `stages/` → 4 个功能段文件夹:
- `find/`      discover, score_auto, commit
- `fetch/`     fetch_oa, recover_oa, recover_agent, fetch_tierb
- `summarize/` build_worklist, summarize_auto, register_summaries, render_topic
- `verify/`    verify_summaries, correct_summaries, escalate_verify

配套:
- 用 `git mv` 挪(14 个全部识别为 rename,历史保留);各段加空 `__init__.py`。
- 唯一跨段 import 改 `from summarize.summarize_auto import full_text`(靠 path-shim 把 pipeline/ 入 sys.path + 段有 __init__.py 才解析得到)。
- run.py `steps()`+`run_auto_sum` 13 处路径改 `<段>/<脚本>.py`;**仍 subprocess spawn + cwd=ROOT**(进程隔离/agent 行为不变)。
- 各脚本注释里 Usage 路径 sed 更新;同步 `pipeline/ARCHITECTURE.md` + `CLAUDE.md`,写入**代码组织规范(2026-06-18 定,以后一律遵循):主链按功能段分文件夹**。

## 四、验证(全过)
1. 全量 py_compile 通过。
2. 14 脚本 import 烟雾测试(无参跑看是否 ModuleNotFoundError)全过——含跨段那处。
3. run.py 调度测试:启动的是新路径 `pipeline/find/discover.py`(失败在读不存在的 topic.json,预期内)。
4. git 全部识别为 rename。
> 测试曾往 logs/run.log 写了 4 行噪音(`__notexist__`/recover 空跑),提交前已 `git checkout` 还原,未混入提交。

## 五、规范(以后遵循)
- 加主链脚本 → 放它所属**段文件夹**(没有就新建 段/+空 `__init__.py`),复制 path-shim 三行,在 run.py 的 `steps()`+`AUTO` 注册(路径 `<段>/<脚本>.py`)。
- 旁路放 `tools/`;公共/入口才放根目录。`lib/` 不动。
- 详见 `pipeline/ARCHITECTURE.md`(已更新为事实源)。

## 六、下一步(未做)
- 第一层"找论文"框架已清爽。待办:端到端验一遍**全自动打分自举**(裸跑→autopick 锚点→带锚重打→边界复称→commit),用临时库跑个小主题确认全自动路径真能跑通(06-17 落地后只做过三层验证,没端到端实跑)。
- 或继续往下看取全文/总结/核查段。
