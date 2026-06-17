---
name: score-cross-batch-drift
description: 打分阶段跨批次校准漂移是待修问题；修法三步+必避的z-norm陷阱；明天一起搞
metadata: 
  node_type: memory
  type: project
  originSessionId: cfdbc7ff-12f4-4ae2-b443-9a8bb71629da
---

Research_agent 的 `score_auto` 逐批独立 `claude -p` 打分，批之间无共享参照系 → **跨批次校准漂移**：几分校准噪声落在 target 截断线附近就翻转去留、打乱 rank。用户 2026-06-17 拍板**这个要解决**（打分其它错误形态都收敛成"静默丢/假阴性"，能被多query召回冗余兜住；**唯独漂移兜不住**——冗余补回被漏的论文，补不回被打歪的分）。

**⚠️ 必避陷阱**：绝不能做"逐批 z-score 归一化"——池子被 `discover.prefilter_rank` 预排序过，靠前的批本就更相关，逐批统计归一化会抹平真信号，越治越糟。

**修法三步（性价比叠加，待明天定+过目后再落码）**：①加大 batch_size 10→25/30(近免费,降接缝数) ②每批塞同一组已定分锚点(钉到同一标尺) ③首跑后取截断线±N分窄带在一次调用里重排(真正的校正,绕开z-norm陷阱)。建议①+②先上、③作校正层。

**明天唯一卡点**=范围：只保"截断线去留正确"(③只覆盖边界带) vs 连"选中集内部rank次序"也要稳(③扩范围,更贵)。

落点：`pipeline/stages/score_auto.py`(主体) + 可能 `commit.py`(③边界带依赖选篇逻辑)。**全程没动代码/生产库。** 完整记录见 `logs/SESSION-2026-06-17-score-drift.md`。相关：改库层vs检索层之辩见 [[corpus-as-knowledge-base-rag]]；打分要不要verify闭环(结论:不要照搬summary那套)同会话讨论过。
