# Memory Index

- [总蓝图:三个出口](grand-plan-three-outlets.md) — 用户定稿的最高层 idea:流水线→知识库→本人查/agent查/ARS idea→论文;决策先对齐它
- [流水线使用模式](pipeline-interaction-model.md) — 对话驱动、我当总调度；用户明确不要解耦，检索词要先过目
- [研究论文流水线](research-paper-pipeline.md) — Research_agent 里多源搜论文+中文总结存库的每周流水线；设计决策与首测状态
- [Codex 跨模型评审团](cross-model-codex-panel.md) — 质量闭环(核查→修正→复核,run auto verify 阶段)；2026-06-15 升级:以 PDF 为唯一原文+Codex 自渲染 PDF；v1 幻觉率 ~20% major（重跑对比见下条）
- [论文库变 RAG 知识库](corpus-as-knowledge-base-rag.md) — 大计划：卡住时让 agent 来库里查答案；可行性、检索分阶段路径、"持续学习"正确理解（未动手）
- [记忆与换机器关切](memory-and-migration-concerns.md) — 用户两大痛点已答(change-device/MIGRATION.md);流程细节清单等他回来逐项调
- [Prompt 改进参考调研](prompt-improvement-reference-study.md) — 改 summarize+verify;单 agent 模式。**summarize 侧已实现+测过**(note_plan+接地门+strength+7问,新总结锚点暴增);verify 侧设计中,确认加张冠李戴语义核查+unverifiable 档
- [agent-skills 个人 skill 库](agent-skills-repo.md) — `~/Projects/agent-skills` 独立 git 仓,复制式 `bash install.sh`→`~/.claude/skills/`;首个 skill=planning-with-files;换机器 clone+install
- [新核查重跑+对比(进行中)](verify-rerun-comparison.md) — 用升级流程重跑两主题核查与旧流程逐篇对比;含7条待办+续跑状态(gt16/100,dhi3/129);配额限流非bug;待办#7常驻续跑脚本
- [知识库检索升级调研](kb-retrieval-upgrade-research.md) — 2026-06-17:PaperQA2(RCS)/RAPTOR/GraphRAG 三参考+三步路线;服务"RL训练监控agent带症状来问";用户在搞懂提问阶段,别急着写码
- [打分跨批次校准漂移](score-cross-batch-drift.md) — 2026-06-17:score_auto逐批独立打分→漂移翻转截断线;唯一召回冗余兜不住的错;修法三步(加批量/共享锚点/边界重排)+避z-norm陷阱;明天定范围再落码
- [新旧总结逐篇对照](summary-version-comparison.md) — 2026-06-17:16篇三版对照;新版对agent更好但修正环节会推翻codex正确认定+伪造核对、旁白串正文、v2危险中间态;cron暂停;总结错误待用户深议
- [codex额度烧穿/verify全挂](codex-quota-verify-broken.md) — 2026-06-17:codex verify连挂三班;窗口只够~20次核查;根因4 bug(抓不到真错误→熔断失灵)待修;已调cron 2:00/7:30但只缓解批间;疑批量10→20是诱因
- [打分漂移外部调研](score-drift-external-research.md) — 2026-06-17:落码前先 deep-research 调研漂移成熟解法+LLM做文献筛选的更general范式;含现状bug(rubric硬编码在digital-human主题)
- [人工关卡走Telegram](human-gate-telegram.md) — 用户偏好:要他拍板的关卡(锚点挑选等)除终端也推TG,两边都能审
