---
name: memory-and-migration-concerns
description: 用户两大关切——记忆在哪/换机器怎么办(已建 change-device/MIGRATION.md);流程细节待用户回来逐项调
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cb4b6bc5-45df-47cd-8c89-871d2a127987
---

用户 2026-06-10 上飞机前交代:①先搭大框架,细节他回来再调——"目前这个流程里面**很多细节都要调整**";②点名两个痛点:**我的记忆在哪**、**换机器了怎么办**。

**Why:** 用户在意系统的可迁移性和透明度——agent 记忆是黑盒会让他不安;项目要长期跑,不能绑死在一台机器上。

**How to apply:**
- 权威答案=`change-device/MIGRATION.md`(记忆分布地图+换机器9步清单+全局~/.claude/CLAUDE.md附录)+ `change-device/README.md`(整目录搬迁流程)。被问到"记忆/换机器"先指它们。
- 铁律:**任何只存在于 agent 记忆里的要紧事都必须提升进 CLAUDE.md**(记忆只是影子,不跨机器)。
- 下次用户回来,主动提"细节调整"清单让他逐项过:已知候选=Bipedal去重、codex_panel开关、verify抽检比例、bot常驻策略、suspect措辞(PMLR误flag类)、[[grand-plan-three-outlets]]出口③真实idea试跑。
