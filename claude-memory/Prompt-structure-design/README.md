# design — 横切 / 深度设计长文

定型的、跨模块的设计长读放这（模块自己的设计在 `../modules/<x>/README.md`）。

- `quality.md` — 质量信号四档体系（block/suspect/trusted/flag），横切子系统，find/summarize/retrieve 都认它的标记。
- `summary-design-principles.md` — 总结层设计原则（§八定稿）：总结=分诊层、精度让位 PDF、report-only 核查 + 整篇重做。
- `summary-prompt-rewrite-plan.md` — 总结 prompt 重写方案背景（"为什么这么改"；现行 prompt 以代码为准）。
- `prompts.md` — 打分/总结/核查三件套 prompt 的总账 + 演变史（map+changelog，非镜像）。
- `score-drift-research-findings.md` — 打分跨批次漂移（rubric execution drift）的外部调研 + 修法方案。
- `qa-layer-design.md` — 知识库问答出口（retrieve）的架构设计（金字塔 / 五方案 / 两种模式）。
- `qa-layer-evidence.md` — 上文的实证支撑（论文 / 对比 / 数字汇总，一处可查）。
- `skill-工作原理与调用.md` — Claude Code skill 机制参考。
