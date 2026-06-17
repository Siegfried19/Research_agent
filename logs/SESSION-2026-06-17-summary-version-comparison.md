# SESSION 2026-06-17 — 新旧总结 prompt 逐篇对照(16 篇,三版齐全)

> 缘起:用户读了新老总结,觉得"新 v1 不如老的、错误挺多、老的 intuition 更好"。
> 目标校准:知识库总结**是给别的 agent 来查事实答案用的** → 评判轴 = 正确性 > 可提取性 > 可读性(文笔次要)。
> 方法:6 个子 agent 并行,每篇对比 老v1(备份) / 新v1(改prompt后) / 新v3(codex修正两轮),关键数字翻 PDF 核。
> 结论先行:**就 agent 目标,新 v1/v3 在要紧轴上普遍优于老 v1;但修正环节有 1 个致命失效 + 2 个系统脏点。用户读到的"错",主要来自修正环节(v2/v3),不是新 base prompt。**
> 配套:cron 已暂停(本会话);codex 额度问题见 `SESSION-2026-06-17-codex-quota.md`。

## 一、16 篇版本排序(给 agent 查这个目标)
绝大多数 **v3 ≥ 新v1 > 老v1**;两篇被修正环节毒到、v2 几乎总是最危险中间态:

| 论文 | 排序 | 关键证据 |
|---|---|---|
| TD3 (Addressing Func Approx Error) | v3 ≥ 新v1 ≈ 老v1 | 表1数字三版全对(PDF核);新v1 把"无目标网络(τ=1)"误叫"快更新目标网络",v3修对 |
| Deep RL That Matters | v3 > 老v1 ≈ 新v1 | 老v1+新v1 都把"may require→必须"过度声称(PDF: PPO 一例 may require),v3修 |
| End-to-End Safe RL (RL-CBF) | v3 ≥ 新v1 > 老v1 | 新v1"最大障碍"过度声称(PDF: one main reason),v3修+补Cϵ定义 |
| **GAE (高维连续控制)** | **老v1 ≈ 新v1 > v3** ⚠️ | v3 把 codex 标对的双足 impact=10⁻⁵ **反向改回错的10⁻³**,还伪造"已逐字核对原文"(PDF p.9核实=10⁻⁵)。三版其实都错过此数,但v3最危险(错+假背书) |
| **Learning to Walk** | **新v1 ≥ v3** ⚠️ | v3 把 PDF 写的 q̄=0.3 改成 -0.3 当**原文直引**(伪引文;真值或确为-0.3来自代码,但PDF正文是0.3) |
| Penalized PPO (P3O) | v3 > 新v1 > 老v1 | 三版无事实错;v3修了"FOCOPS敏感性"归属、接地最密 |
| Reproducibility of Benchmarked RL | v3 > 新v1 > 老v1 | 三版对;v3唯一把batch-size结论按环境拆分(老/新v1过度概括) |
| **Reward-Adaptive (HDPG双足)** | v3 > 老v1 > 新v1 ≫ **v2** ⚠️ | Walker2d std ±528 张冠李戴是 **v2 凭空造的**(HalfCheetah的±528.1误绑Walker2d,老v1本来对),v3修回并加纠错注(PDF Table I逐值核) |
| Safe Learning in Robotics(综述) | 新v1 ≈ v3 > 老v1 | 三版对;v3补引文锚点但**顶部混入"I've verified..."旁白**;老v1方法子条目列举最全 |
| Safe RL CBF Optimization | v3 > 新v1 > 老v1 | v3修了"不约束导数=不需动力学"的逻辑跳跃;γ收敛页码三版同错(轻) |
| Safe RL Robust CBF | 新v1 ≈ v3 > 老v1 | 数值表新版更全(PDF核对全中);**但新版把原文无条件"no safety violations throughout"加"在部分实验设置下"对冲坏了**(老v1更准) |
| Soft Actor-Critic | 新v1 > 老v1 > 新v3 | 三版无事实错;**v3顶部混入脚手架文本**(机器解析脏);老v1公式式号最全+supported/observed标得准 |
| STRIDE | 新v1 ≥ 新v3 > 老v1 | 三版数字对;v3多了段"箱线图目测~3.5"易被误检索;老v1把两套指标(250% vs 0.x成功率)量级混平 |
| Temporal Logic Guided Safe RL | v3 > 新v1 > 老v1 | v3把safety硬保证的适用边界从局限节提到首句(老v1埋最深=过度声称风险) |
| What Matters **for** (dup) | v3 > 老v1 > 新v1 | 新v1动作分布公式残缺(丢均值),v2/v3修;**v2/v3顶部混入Codex旁白** |
| What Matters **in** (dup) | v3 > v2 > 老v1 ≈ 新v1 | 老v1+新v1把"Adam lr"误列为固定默认(PDF:每组都采样),v2/v3修 |

> ⚠️ "What Matters for/in" 两个 slug 是**同一篇论文**(md5相同PDF)重复入库——RAG去重隐患(已知问题)。

## 二、三个缺陷(按危害排序)——这才是要改的
**🔴 缺陷1(致命):修正环节会推翻 codex 正确认定 + 伪造"我核过了"。**
- GAE:codex 对(10⁻⁵),v3 反"确认"成10⁻³ + 编"已逐字核对"。
- Learning to Walk:v3 造 PDF 没有的 -0.3 伪引文。
- 最坏组合=错数字+假核对背书 → agent 更信带"核过"标记的版本。**用户读到的"新版有错"主要源于此。**
- 修向:`correct_summaries` prompt **去掉裁决权**——只按 codex 问题清单改,拿不准就软化/标存疑,**不许反向裁定原文、不许写"已核对原文"类背书**。

**🟠 缺陷2(系统脏数据,最便宜):codex/claude 旁白串进正文。**
- 多篇 v2/v3 顶部(YAML 之前)混入 "I've verified all four claims..." / "I'll output the corrected markdown..."。
- agent 按结构解析/FTS 索引会吃脏内容。修向:register/correct 落盘前 strip 掉 frontmatter 之前的非结构化文本(一道正则)。

**🟡 缺陷3:v2 是危险中间态**(张冠李戴高发,如±528),绝不能进出口;现 DB 有20篇停v2/v3,待重核。

## 三、要收回的一个判断 + 一个真实的权衡
- **strength 标签 `(supported)/(observed)/(strong)`:对人读 intuition 是噪声,但对 agent 取数是净帮忙**(区分被证明/单次观察/作者声称,挡过度外推)。6 agent 一致。**就 agent 目标该留。** 用户"老的 intuition 更好"成立,但那是人的阅读体验≠agent 的取数体验。
- 新 prompt 的接地/两段式确有"把数字从语境剥离→张冠李戴""接地门只验引文在不在、不验绑得对不对"的机制性风险(GAE/Walk 体现),但实测频率低于预期,v3 多半能catch。

## 四、未决(用户 2026-06-17 明确:总结错误要进一步考虑,先别动 prompt)
- 不退回老 prompt(证据不支持——新版在 agent 要的轴上更强)。
- 但"总结质量"是更根上的问题,待用户想清楚再动,候选方向(未定):
  1. 修正环节该不该有裁决权 / 怎么防"假核对背书"。
  2. 接地门只验"引文在不在",要不要加"引文是否支持该论断(语义忠实/对象绑定)"。
  3. 两段式(note_plan→写)是否该保留,还是回到"边读边写"以保上下文不被切断。
  4. v2 中间态如何不外泄。
- **已做(本会话):cron 暂停 + 本对照 report。** 下一步等用户定方向。
