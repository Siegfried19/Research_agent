# claude-memory —— agent 跨会话记忆的仓库内快照

这是 Claude Code 给本项目维护的"跨会话记忆"的一份**快照**，拷进仓库是为了**换机器时能跟着项目目录走（随 git / 随整盘打包）**。

## 它原本住在哪
全局区，且**按项目路径绑定**（不在项目目录里，所以搬项目目录带不走）：

```
~/.claude/projects/-home-siegfried-Projects-Research-agent/memory/
```

那串目录名 = 项目绝对路径把 `/` 和 `_` 都换成 `-`。**新机器路径一变，这个名字就变，老记忆对不上号** —— 这正是要在仓库里留一份的原因。

## 里面是什么
`MEMORY.md` 是索引（一行一条）。其余 `*.md` 各是一条记忆，三类：
1. **用户偏好/拍板**（代码里看不到）：总蓝图三个出口、流水线不解耦、检索词先过目、关卡推 Telegram……
2. **进度状态**（时效性强、丢了就没）：核查重跑对比、codex 额度/verify 挂、打分漂移、新旧总结对照……
3. **在调研未动手的方向**：RAG 知识库、检索升级、prompt 改进。

## 新机器落地后怎么回灌（二选一）
1. **直接回灌**到新路径对应的记忆目录（推荐）：
   ```bash
   # 新机器上先确认新 slug：在项目里开一次 claude 看 ~/.claude/projects/ 下生成的目录名
   mkdir -p ~/.claude/projects/<新-slug>/memory
   cp -a docs/claude-memory/*.md ~/.claude/projects/<新-slug>/memory/
   # 注意别覆盖这份 README（它是仓库说明，不是记忆条目，回灌时可跳过）
   ```
2. **或**就让它留在仓库里当文档读 —— Claude 开会话会读 `CLAUDE.md`，要紧的事本就应提升进 `CLAUDE.md`，这份快照是兜底。

> 维护提醒：这是**快照**，不会自动跟全局记忆同步。换机器前最好重拷一遍最新的：
> `cp -a ~/.claude/projects/-home-siegfried-Projects-Research-agent/memory/*.md docs/claude-memory/`
