---
name: agent-skills-repo
description: "用户的个人全局 Claude Code skill 库,独立 git 仓 ~/Projects/agent-skills,复制式安装到 ~/.claude/skills"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7cda1bc1-f8f8-42f9-bc2d-f9da21a09d93
---

用户 2026-06-16 把 claude-scholar 的 `planning-with-files` skill 抽出来,建了一个**独立的个人全局 skill 库**(跟项目解耦,以后自己要的 skill 都往这放)。

- **位置**:`~/Projects/agent-skills`(跟 Research_agent 平级,独立 git 仓;branch=main;commit 已建;**远端待用户自己 push**——本机无 gh)。
- **结构**:`README.md` + `install.sh`(复制式) + `skills/<name>/`(每个自包含,含 SKILL.md)。当前唯一 skill=`planning-with-files`(抽自 claude-scholar MIT,思想源自 Manus context engineering:task_plan.md/notes.md/deliverable.md,治 agent 长任务忘目标/丢上下文/偷偷重试)。
- **安装方式=复制(用户选的,非软链)**:`bash install.sh` 把 `skills/` 各目录复制覆盖进 `~/.claude/skills/`。`~/.claude/skills/` 里是**独立拷贝**,与本仓库解耦(仓库可挪/删不影响已装的)。
- **换机器**:`git clone <repo> ~/Projects/agent-skills && cd ~/Projects/agent-skills && bash install.sh`。**更新**:`git pull` 后**重跑 `bash install.sh`**(复制不自动同步,有意如此)。**加新 skill**:往 `skills/` 丢新目录,重跑 install。
- ⚠️ user-level skill 一般**下个 Claude Code 会话**才被发现。

关联 [[prompt-improvement-reference-study]](planning-with-files 来自调研 claude-scholar 时的支线)。
