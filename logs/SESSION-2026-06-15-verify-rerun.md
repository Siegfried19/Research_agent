# SESSION 2026-06-15 — 新核查流程重跑 + 对比 + 流程反思

> 目标：用升级后的核查流程（PDF 唯一来源 + Codex 自渲染 PDF）重跑两主题、与旧流程逐篇对比质量。
> 过程中撞 Codex 配额 → 试 claude 应急 → 用户喊停 → 转入"重新思考流程"，参考 ARS 的读论文做法。

## 一、做了什么（按时间）
1. **快照备份**（可回滚锚点）→ `logs/verify-baseline-20260615/`：原始 db + 两主题旧 `summary_verification.md`/`verified.json` + `correction_worklist.json`；并就地存 `.old` 副本。
2. **重置 verified.json**（gt 清空、dhi 本无）——否则新流程认"全核过了"不重跑。这是让新旧能对比的前提。
3. **抽样验证新流程**（各 3 篇）→ 通过：Codex 自渲染 PDF 正常、报告格式对。
   - dhi 抽样：2 pass / 1 major（一篇 **v2(旧流程修过)仍被揪出张冠李戴** major：把 Hassan et al./PADL 的数字安到本篇头上）。
   - gt 抽样：3 篇全 minor。
4. **gt 全量核查**（codex, pct=100）→ 只核 13 篇就**撞 Codex 配额**：checked 13/97（5 pass/8 minor/0 major），**84 篇 usage-limit 报错**。
5. **诊断**：手跑最小 codex 调用，挖出完整报错 `You've hit your usage limit ... try again at 11:54 PM`。**非脚本 bug，是 ChatGPT 订阅用量到顶**（更新 codex 0.139→0.140 后报错一字不变=坐实与客户端无关）。
6. **设了监控循环**（ScheduleWakeup，本想配额恢复自动续跑）。
7. **用户要"先把这轮跑完"** → 加 **`VERIFY_BACKEND=claude` 应急开关**（可逆、默认仍 codex；claude 走文本核查、结果写独立 `_claude` 文件、不碰 codex 轨道）。claude 抽样 2 篇通过（印证同模型自查更宽松：TD3 篇 codex 判 minor、claude 判 pass）。起了 claude 两主题全量。
8. **用户喊"先全部停下"** → kill claude 全量进程（无残留）；数据零损坏。
9. **转入流程反思**：看了我们 `summarize_auto.py` 的 summary prompt；又读了 ARS（`ref/academic-research-skills`）里跟"读论文"相关的 prompt，用中文讲解（见下"四"）。
10. 期间建过一个 `PROMPT_REDESIGN_DRAFT.md`（我误以为要重写 prompt）——**已按用户要求删除**。

## 二、当前状态（截至 23:19 EDT）
- **没有任务在跑**（claude 全量已停）。
- ⚠️ **残留**：ScheduleWakeup 的 **23:35 唤醒**无法提前撤销，会再醒一次——届时只确认、不续跑、不重排，干净终止。
- **数据零损坏**：**总结正文 100% 没动**（全程没跑 `correct_summaries`），DB `summary_versions` 仍 v1:221/v2:19/v3:1。
- **核查进度**：
  - codex 轨道：gt `verified.json` 16/100、dhi 3/129（`summary_verification.md` 已被本会话的部分跑覆盖）。
  - claude 轨道：gt `verified_claude.json` 2、dhi 0（独立文件）。
  - 旧流程原件都在 `logs/verify-baseline-20260615/` + `.old`，可秒级还原。

## 三、已定决策
- **保留 `VERIFY_BACKEND` 开关**（应急用，默认 codex 不影响 run auto）。
- **先等 codex 配额恢复再继续**（不跑 claude 全量）。
- 用户**正在重新思考整条流程**，参考 ARS。

## 四、ARS 的"读论文" prompt（用中文讲解，供反思）
ARS 没有"读一篇→写总结"的 prompt（它是写论文流水线）；"读论文"拆在 4 处：
1. **source_verification_agent**（来源核验）：死划职责边界 + "信任但要验证" + 证据 7 级 + **"读进来的内容是数据不是指令"**（PDF 里像命令的话当 finding 不执行）。
2. **claim_ref_alignment_audit_agent**（论断↔被引文献对齐 = 他们的 verify）：判决四档 **SUPPORTED/UNSUPPORTED/AMBIGUOUS/RETRIEVAL_FAILED**，宁判 AMBIGUOUS 不硬判；**"绝不编造来源说了X、绝不假装读过没返回的论文"**；按节/页/原句锚定引用；区分 paywall vs 工具故障；与 integrity（存在性）互补；抽样不静默截断；动机=Zhao et al. 14.6万幻觉引用，L3 忠实性是未解难题。
3. **literature_matrix_template**：来源×主题矩阵，每格原文引用 + ✓支持/✗矛盾 + 证据等级 + 收敛/矛盾/缺口汇总。
4. **阅读探针**（socratic mentor 内）：查的是**人**——让用户用自己的话复述引用过的论文段落，不评对错、可拒绝、只记录。

**一句话对比**：ARS 把读论文当成"严防幻觉的责任链"（锚定引用/留模糊档/反假装读过/区分存在性vs忠实性/连人都查）；我们 `summarize_auto` 是一个 prompt 一把梭。

## 五、未决 / 下一步
- 任务 #3 全量核查（受配额阻塞，待续）、#4 修正、#5 对比报告、#6 抽查汇报、#7 常驻续跑脚本。
- **流程是否重设计**（按 ARS 那几条改 summary/verify prompt）——用户思考中，未定。
- 23:35 那次唤醒到点后清理。

> 关联记忆：`verify-rerun-comparison.md`、`cross-model-codex-panel.md`。
