---
name: pipeline-interaction-model
description: 用户定的流水线使用模式：对话驱动、agent 当总调度，不追求与 Claude 解耦
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 07f08fcc-a250-48a6-a70a-b9f36772e835
---

用户（2026-06-10）明确：**不要把流水线和我解耦**，要的是流畅的对话驱动。固定模式：
- 开新主题 = 用户来聊研究思路 → 讨论边界 → 我把思路翻成英文检索词**给用户过目确认** → 建 topic.json → 我后台起 `run.py auto` + 挂监控（盯日志、修问题、汇报漏斗数据）。
- 每周增量 = 用户说一句，我跑同一条命令、盯完汇报。
- 总结/打分由脚本内 `claude -p` 完成（= 每篇一个无头子 agent），我是调度和监工，不亲自在会话里逐篇总结。

**Why:** 用户曾被建议加 `new_topic.py` 实现全脱离对话；用户拒绝——检索词质量需要讨论迭代，且他就喜欢通过对话操作。
**How to apply:** 别再提议"让流程脱离 Claude 会话"；新主题时主动进入讨论模式，检索词先展示再写库；跑长流程用后台任务 + Monitor，只在出问题/里程碑时汇报。相关：[[research-paper-pipeline]]
