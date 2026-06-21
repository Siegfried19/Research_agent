# summarize — 写中文结构化总结（定型设计）

> 用 `claude -p` 给每篇论文写一份**中文**结构化总结，落盘 + 注册进 `summary_versions`。
> 代码：`pipeline/summarize/`；上游原则长文 `claude-memory/Prompt-structure-design/summary-design-principles.md`（§八定稿）、`claude-memory/Prompt-structure-design/prompts.md`（现行 prompt 总账）。

## 这个模块干什么 / 边界
- **输入**：库里 `status='source_ready'` 的论文（fetch 段已把 PDF 落到 `storage/sources/<slug>/paper.pdf`）。
- **干的事**：claude 直读 PDF（Read 工具，看得到公式/图/表）→ 写中文总结 → 存 `storage/sources/<slug>/vN.md` → 注册版本、置 `status='summarized'` → 渲染主题视图 `topics/<id>/topic.md`。
- **不管**：取 PDF（fetch 段）、核查幻觉（verify 段，Codex）。本模块**不做事实核查**——只在 verify 判出 major 后被回调做「整篇重做」（见下）。
- **首要消费者是别的 AI agent**（其次研究者本人）：它检索到一篇时靠这份总结判断"方法是什么、值不值得打开 PDF 深读"。判断轴：**正确性 > 可提取性 > 文笔**。

## 关键脚本（run auto 里的 worklist / sum / finalize 三步）
- `build_worklist.py <id>` — 查 `source_ready` 篇（按 rank，**排除 `kind='web'` 的 source——web 正文不进总结**）→ `topics/<id>/summarize_worklist.json`。
- `summarize_auto.py <id> [并发] [--limit N]` — 每篇一次 `claude -p`（默认并发 2，PDF 模式重）。幂等：`summary_path` 已存在则跳过。`--limit N` 取 rank 前 N 篇未做的（夜间 cron 用来按 token 窗口封批）。无 PDF 不回退纯文本，记 `summarize_no_pdf.log` 跳过。**含 `resummarize()`**（见下，被 verify 段回调）。
- `register_summaries.py <id|all>` — 把 v1.md 注册进 `summary_versions`、置 `status='summarized'`。
- `render_topic.py <id>` — 渲染 `topics/<id>/topic.md`（排名表 + 相关性理由 + 库内引用边 + suspect 单列"低可信来源"节）。

## 核心设计原则（稳定，勿轻改）
1. **总结 = 方法/直觉的「分诊层」，不是「权威数字库」。** 两段式心智：① 读总结判"值不值得深入" → ② 觉得值得才去 PDF 看精确细节。没有一种消费者真的需要总结给精确数字，而 **PDF 始终在盘上**，随时可取。
2. **精度让位 PDF。** 给量级/方向即可；确需写具体数值就**紧跟出处**（"约 0.3，见 §5.2 表3"）且不当结论卖点。反直觉但关键：斩钉截铁写"10⁻³"反而**引诱消费者直接信、不去 PDF 核**——具体数字应"克制 + 显式指向 PDF"。
3. **只用本 PDF。** 所有事实/数字/公式只能来自这份 PDF；原文没写到写 `[原文未提]`，不靠记忆脑补。**反向也守**：不轻易断言原文"没有/未给出"某内容（你没读到≠不存在，附录常在后几页）。
4. **边读边写 + 7问自查**（2026-06-18 起，去掉了旧的 note_plan/接地门两段式——实测制造"无锚论断"假阳性洪水 + 接地门只验引文在不在、防不住张冠李戴，危害>收益）。通读全文 PDF（>20 页用 pages 分批读完，含附录）→ 写总结 → 写完逐条 7 问自查（方向准不准/有没有讲直觉/适用边界/接地+防张冠李戴/数字克制/原子可提取/证明 vs 没证明），不达标回去补再定稿。
5. **论断原子化 + 内联 strength。** 一句一个点（便于 agent 单独抽取）；方向性结论句末标 `observed | supported | strong`，**措辞不许超过 strength**（observed 不许写成"全面超越"）。模板含一等段落"适用边界（什么时候管用/不管用）"。
6. **质疑模式（suspect 来源）。** `quality_tier='suspect'`（掠夺刊名单命中）→ prompt 注入批判指令：开头加来源警示行、结果写"作者声称"、strength 封顶 observed、"局限与我的质疑"≥5 条主动找硬伤。`flag`（预印本）→ 正常总结但注一句"未经同行评审"。
7. **resummarize = 整篇重做，无裁决权**（取代旧打补丁式 `correct_summaries`，已删）。verify 判出 major 时回调 `resummarize`：**从 PDF 重新写一份全新 vN+1**，复用 build_prompt 全套机制；核查问题清单只当**避坑提示**喂进去，prompt 明令：
   - **不许据清单反推原文对错**（核查员也可能判错，一切以你亲读 PDF 为准）；
   - **不许照搬旧版**措辞/结构；
   - **绝不许写"已核对原文""经核实"类背书**（你的工作是忠实转写，不是给自己背书）。
   - 根治旧 `correct_summaries` 那个"反向裁决核查员 + 伪造核对背书"的致命 bug（见 `logs/SESSION-2026-06-17-summary-version-comparison.md`）。

## 接口 / 落盘约定
- 文件名用 `sources.slug`（不是 DOI）；DOI 仍是 `sources.id` 主键。
- 总结 markdown 以 YAML front matter 开头（`paper_id/version/based_on/created_at/note`）；export/更新流程要解析这段头，`clean_output()` 砍掉 front matter 之前的寒暄。
- 输出校验：必须以 `---` 开头、含 `## 一句话`、长度 ≥200 字符，否则判 bad output 重试。

## 坑
- claude -p 偶撞 Max 限流 → 重跑该阶段即可（幂等，已做的跳过）；撞限流就调小并发：`summarize_auto.py <id> 1`。
- 无 PDF 的 summarized 篇 = 异常（PDF 丢了）；resummarize 同样无 PDF 跳过。
- 超时放宽到 1200s（多页 PDF + 7问自查 turn 数多）。
