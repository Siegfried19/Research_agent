---
name: grand-plan-three-outlets
description: 用户定稿的最 high level 蓝图——流水线→知识库→三个出口(本人查/agent查/ARS idea→论文)
metadata: 
  node_type: memory
  type: project
  originSessionId: cb4b6bc5-45df-47cd-8c89-871d2a127987
---

用户 2026-06-10 定稿的**总蓝图**(最 high level 的 idea,做任何决策先对齐它),三层架构、下层喂上层:

1. **论文自动下载+总结流水线**(已建成)——[[research-paper-pipeline]],每周 `run auto`。
2. **相互关联、有方便接口的知识库**(建设中)——[[corpus-as-knowledge-base-rag]],SQLite+引用图+`ask.py`(FTS5 已落地)。
3. **知识库的三个出口**(按近→远):
   - ① 用户本人来查答案(`ask.py --answer`,已有);
   - ② **别的项目里的 agent** 做用户给的任务、卡住时来查(`ask.py --json` 绝对路径)——用户明确说"来提问的只会是别的 agent",接口按机器消费者设计;⚠️ **全局 `~/.claude/CLAUDE.md` 发现机制指针 2026-06-16 已撤回(ask.py 还没修好),所以出口②目前是半成品,待就绪再加回**;
   - ③ 🎯 **idea→论文流水线**:用 academic agent(`ref/academic-research-skills`,ARS,CC BY-NC 非商用)吃这个库,从研究想法走到论文成稿。接口=ARS deep-research 的 corpus-first 模式吃 `literature_corpus[]`,导出器是小工作量。**未动手,是知识库的终极验收标准。**

**Why:** 此前待办只覆盖到出口①②;出口③(idea→论文)是用户本次新明确的终极用途,此前从未进过正式计划。

**How to apply:** 评估任何新功能/重构的优先级时,问"它服务哪个出口";知识库接口设计永远优先考虑 agent 消费者(机器可读、绝对路径、质量标记外露);ARS 集成动手前先做 literature_corpus 导出器 + 认 quality_tier。
