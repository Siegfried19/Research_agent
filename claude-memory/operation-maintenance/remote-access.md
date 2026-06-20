# 远程访问 — 远程查库（SSH）+ 手机过验证看屏（已封存）

> 整合自 `remote-access/`（README/SETUP/MEMORY-SNIPPET）+ CLAUDE.md「手机过验证」节（2026-06-20 搬进 ops/）。
> 这里有两件不相干的"远程"事：
> 1. **远程查库**（SSH）：让别的机器上的 agent 来查这个文献库——**已备好、尚未启用**。
> 2. **手机过验证看屏**（noVNC/x11vnc）：Tier B 抓取时手机远程点掉付费墙验证——**已封存 MOTHBALLED，默认关**。

---

# 一、远程查库（SSH 远程执行 ask.py）

## 拓扑

这台机（`siegfried-laptop-server`）是**专门常开的服务机**，挂着整个文献库（SQLite 库 / PDF 全文 / GPU 嵌入引擎）。别的机器（主力机）当**客户端**，通过 SSH 远程跑这台机上的 `ask.py` 来查库——**客户端什么都不用装**。

```
主力机(客户端) ──ssh──▶ siegfried-laptop-server(服务机)
  Claude/agent          data-base/papers.sqlite + storage/papers/
  卡住来查    ◀─stdout─  GPU 嵌入 + vec.sqlite + ask.py←真正在这跑
```

**为什么 SSH 远程执行、不是 sshfs 挂文件夹**：库的"大脑"不只是文件，还有 GPU 嵌入引擎（CPU 慢 ~100×）和会被网络文件系统写坏的 SQLite。SSH 远程执行让**计算永远留在有 GPU 的服务机上**，主力机只收文本结果。

## 怎么用（主力机上，配好之后）

```bash
# 机器可读（给 agent）：返回 {answerable, answer, sources:[...]}
ssh research-kb 'cd ~/Projects/Research_agent && python3 pipeline/ask.py "你的问题" --json'

# 人看的综合回答
ssh research-kb 'cd ~/Projects/Research_agent && python3 pipeline/ask.py "你的问题" --answer'

# 深读某篇：--json 里的 summary_path / pdf_path 是服务机上的路径，再 ssh 读
ssh research-kb 'cat <summary_path>'
```

`research-kb` 是主力机 `~/.ssh/config` 里的 SSH Host 别名（见下）。

## 启用步骤（全在主力机上做，服务机不用改代码）

服务机信息：主机名 `siegfried-laptop-server`、用户 `siegfried`、仓库 `~/Projects/Research_agent`。

**0. 先决定网络地址**（服务机当前**没装 Tailscale**，二选一）：
- **Tailscale（推荐，跨网络/公网外都能连，加密）**：两台都 `tailscale up`，记下服务机 tailnet IP（服务机上 `tailscale ip -4`）。
- **同一局域网**：用服务机局域网 IP 或 `siegfried-laptop-server.local`（mDNS）。

**1. 配 SSH 免密 + Host 别名**：
```bash
ssh-keygen -t ed25519              # 一路回车（已有就跳过）
ssh-copy-id siegfried@<服务机地址>   # 输一次密码，之后免密
```
主力机 `~/.ssh/config` 加：
```
Host research-kb
    HostName <服务机地址>
    User siegfried
    # Tailscale 走默认 22；服务机改过端口加 Port xxxx
```

**2. 测连通**：
```bash
ssh research-kb 'echo OK; cd ~/Projects/Research_agent && python3 pipeline/ask.py "test" --json | head -c 300'
```
看到 `OK` + 一段 JSON（`answerable`/`sources`）即通。首次跑向量要加载 GPU 模型，可能慢几秒，正常。

**3.（可选）装 wrapper**，命令更短。把下面这段存成 `~/.local/bin/ask-research-kb` 并 `chmod +x`：
```bash
#!/usr/bin/env bash
# ask-research-kb — 瘦 SSH wrapper，参数原样转发给服务机上的 ask.py
host="${RESEARCH_KB_HOST:-research-kb}"
ssh "$host" "cd ~/Projects/Research_agent && python3 pipeline/ask.py $(printf '%q ' "$@")"
```
之后 `ask-research-kb "你的问题" --json`（默认连别名 `research-kb`，可用环境变量 `RESEARCH_KB_HOST` 覆盖）。

**4. 贴记忆指针**：把下面这节粘到主力机的全局 `~/.claude/CLAUDE.md`，之后主力机上任何 project 的 Claude 卡住都会主动来查：
````markdown
## 论文知识库（卡住了先来查）
有一个持续维护的研究论文库（RL/数字人/安全RL/奖励设计等，中文结构化总结 + PDF 全文，每周增长）。
做任务遇到算法/方法/文献问题，先查它再上网搜：
```bash
ssh research-kb 'cd ~/Projects/Research_agent && python3 pipeline/ask.py "<问题>" --json -n 5'
```
- 返回 JSON：`answerable` + `sources[]`，每条带 `summary_path`（中文总结，先读）和 `pdf_path`（全文，要细节再读）。
- `quality_tier`：`suspect`=来源可疑慎引、`flag`=预印本未经同行评审。
- `answerable=false` 就是库里没有，别硬编，换关键词或上网搜。
（同机的别的 project 不用 SSH，把 `ssh research-kb '...'` 换成本地 `python3 ~/Projects/Research_agent/pipeline/ask.py "<问题>" --json -n 5`。）
````
（此 snippet 提到的 `~230 篇` 等数字按当前库实际调整；上面是当前 `ask.py --json` 的真实字段。）

**5. 冒烟验证**：主力机随便开个 project 的 Claude，问一个库里应有的 RL 问题，看它会不会主动 ssh 去查并正确处理 `answerable=false`。

## 当前状态：已备好、尚未启用

启用所需的 wrapper 脚本 / 全局 snippet 都已内联在上面（原 `remote-access/` 目录在 2026-06-20 文档重构时移除，内容并入本文）。建议**等库填实再启用**：
- 库目前**只有 ~39 篇有总结**（库共 221 篇），用户打算重做总结；重做完、`run <id> index` 跟上后再对外开放更划算。
- 全局指针节 2026-06-16 曾因 `ask.py` 没做好被撤回；现 6-18 检索层升级完毕（混合召回 + rerank + 闭集回答），这次是稳妥重新放出。

### 排错速查
- `ssh research-kb` 连不上 → `ssh -v research-kb` 看卡哪；Tailscale 检查两台都 `up`。
- 连上但 `ask.py` 报错 → 服务机环境问题，到服务机本地直接跑 `ask.py` 复现。
- 服务机睡眠/关机 → 查不到。它本该常开；设过自动休眠就关掉。

---

# 二、手机过验证看屏（noVNC/x11vnc）—— ⚠️ 已封存 MOTHBALLED

> 用途：Tier B 抓付费墙撞 Cloudflare Turnstile / Duo 时，**不在机器旁也能用手机远程点掉验证**。
> **2026-06-10 封存（用户觉得有风险）。代码保留但默认关**——不自动启动、不广播。除非显式开 `config tier_b.remote_view=true` 或环境变量 `RESEARCH_REMOTE_VIEW=1`，否则 `fetch_tierb` 的 `ensure_remote_view()` 直接返回空串，tierb 行为如旧（在机器旁点验证）。

## 机制（留档备用）

`pipeline/remote_view.sh` 把 `:1` 桌面经 **x11vnc（仅 localhost）+ websockify/noVNC（绑 Tailscale IP `100.83.75.76:6080`，VNC 密码，不开 Funnel）** 暴露成网页。开启时 tierb 弹验证会 Telegram 带 noVNC 链接 → 手机点链接 → 看机器 Chrome → 点掉验证 → 续跑。

- 密钥 `config/x11vnc.{pass,plain}`（gitignored）。
- noVNC 在 `dependencies/novnc`（1.4.0，带双指缩放，gitignored）。
- ⚠️ 验证**必须点在机器那个 Chrome 上**（cf_clearance 绑指纹+IP），手机只能远程看屏、不能本地解。

## 若日后解封，要先解决的遗留问题

1. **手机端双指缩放放不大**：用户反馈仍放不大（noVNC 1.4.0 已装，URL `resize=scale`，待查 viewport/手势）。
2. **用户安全顾虑**：虽已 localhost-only + tailnet + 2FA，用户仍觉有风险——这是封存主因。

## 换机器要重建（默认不装）

x11vnc / websockify / `dependencies/novnc` 重新装 + 密钥重新生成（`config/x11vnc.*`）。详见 `migration.md` 封存件一条。

## 相关文件

- `pipeline/ask.py` —— 知识库查询入口（FTS + 向量混合召回 + rerank + 闭集回答）。
- `pipeline/fetch/fetch_tierb.py`（`ensure_remote_view()`）+ `pipeline/remote_view.sh` —— 手机看屏机制。
</content>
