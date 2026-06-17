---
name: cross-model-codex-panel
description: Research_agent 的「Codex 跨模型评审团」——已落地成质量闭环(核查→修正→复核,run auto verify 阶段);2026-06-15 升级为以 PDF 为唯一原文来源 + Codex 自渲染 PDF;实测 v1 总结幻觉率 ~20% major
metadata: 
  node_type: memory
  type: project
  originSessionId: db005934-4862-4bf5-afeb-b160413b79d8
---

用户想把论文**筛选/评价环节**从单 agent 打分升级成**混编模型的小评审团**(Claude+Codex 平级，不是主从/复核)。动机=ARS 的核心论点：同模型自检共享盲点，换训练分布不同的模型互补。

**真实心智模型**：用户看了参考库 ARS(`ref/academic-research-skills/`，纯提示工程的 Claude Code 学术 skill 套件，38 agent 全是 Claude 演不同角色)，想要"一个任务里一排 agent，一部分 Claude 一部分 Codex"。但**现状**：`score_auto.js` 是单 `claude -p` 调用，**还不是多 agent**——所以要两步：①先把单 agent 打分改成评审团；②成员混编模型。

**最小落地方案(讨论达成)**：
- 评审团缩到 2 席：相关性审(Claude)+ 魔鬼代言人(Codex，专挑"该拒"理由，换模型挑刺最值钱)。来源质量**别用 LLM**，用硬名单(掠夺刊/venue 白名单)——又快又免费又准。
- Codex 走 **ChatGPT 订阅**(对称 `claude -p` 蹭 Max，零额外 API 花费)。本机**暂未装** codex CLI：装法 `npm i -g @openai/codex`(全局装在 ~/.nvm，无需 sudo) + `codex login`(浏览器授权，只能用户本人点)。
- 工程上：加 `pipeline/lib/codex.js`，照抄 `lib/claude.js`(spawn 子进程+并发池 pool)，只把 `spawn('claude',['-p',...])` 换成 `spawn('codex',['exec',...])`；`score_auto.js` 按角色路由到不同后端。

**优先级判断(已跟用户对齐)**：先做免费硬信号(掠夺刊名单+venue 白名单)挡 95% 垃圾，panel 是**补充层**不是替代。跨模型对"相关性"这种主观判断大概率高度一致，价值主要在边界篇。成本：单 agent→2 席 ×2 调用，放大到 200 篇两个订阅都可能撞限流。

**状态(2026-06-10:两层全部落地)**：
- **硬信号层**——`pipeline/lib/quality.py` + `config/quality/` 名单(Beall's 衍生+本地追加+DOI前缀黑名单(IJISRT=10.38124)+venue白名单)。2026-06-10 起改**"标记优先"**:名单命中=suspect 入库带标记(总结自动质疑模式),只有撤稿+DOI前缀才 block。
- **Codex 评审团**——codex CLI 已装已登录(ChatGPT 订阅)。`lib/codex.py`(codex exec + --output-last-message);打分魔鬼代言人(config `quality.codex_panel` **默认关,用户 2026-06-10 拍板:打分侧保持关,异议火力集中总结侧**);**Codex 无否决权**。
- **质量闭环(2026-06-10 建成,细节见 CLAUDE.md"跨模型评审团"节)**:verify_summaries(Codex 核查,verified.json 记已核版本) → correct_summaries(claude 拿全文+问题清单重写 vN+1) → 自动复核;escalate_verify=升级阶梯驱动("命中就扩面",--start-pct 100=全量),已进 run auto 的 verify 阶段(新总结入库即核查)。
- **关键实测数据(topic2,100 篇全量)**:v1 总结真实幻觉率 **~18-25% major**(典型:方法梯度方向写反、消融结论说反、"全部任务大幅超越"夸大、作者声称被当事实);修正闭环有效(18 篇修正后复核 0 major 残留,AFU 修了 2 次)。**结论:verify 是必要工序,不是可选抽检**。
- **运维坑**:Codex 配额一窗口 ~90-100 次调用,全量核查会撞墙;verify_batch 有熔断,escalate 断点续传(verified.json 按轮落盘),等配额重置(~5h 窗口)重跑即续。
- 注意常**有第二个 Claude Code 实例同时在改本仓库**——编辑前先读最新。

**2026-06-15 升级**：
- verify/correct **统一以 PDF 为唯一原文来源**(commit 0d0ce64)：summarized 篇必曾有 PDF，没 PDF=异常记错跳过，**绝不退回 text_path 偷换来源**去核一份本就从 PDF 写出来的总结。
- Codex **自渲染 PDF**(26c3bb8)：默认 `verify.codex_self_render=true`——把 paper.pdf 拷进隔离 tmp 目录(workspace-write 沙箱)，Codex 自己 pdftotext 查数字 + 涉及公式/图/表时 pdftoppm/PIL 渲染相关页成图再看。关掉=省钱模式(喂 pdftotext 文本，看不到公式图表)。
- hunt/sum 加"张冠李戴"防线(b5dafc1/145c94a)：校验抽出全文确属该篇 + sum 直读 PDF。
- **用新流程重跑两主题、与旧流程逐篇对比质量**=独立进行中任务，待办/续跑进度/baseline 快照见 [[verify-rerun-comparison]]（已实测：digital-human 一篇 v2 旧流程修过的仍被新流程揪出 5 条"张冠李戴"型 major，证明新流程有增量）。

关联 [[research-paper-pipeline]]。ARS 跨模型机制原文见 `ref/academic-research-skills/shared/cross_model_verification.md`(它用 curl 打 OpenAI/Gemini API 做引用核验，不是 Codex CLI)。
