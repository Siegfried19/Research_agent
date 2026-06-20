# dependencies/ — 大体积外部依赖统一目录

第三方 / 可重新下载的大依赖都放这里，**不入 git**（`.gitignore` 里 `dependencies/*` 忽略，只留本 README）。
换机器：整目录拷会带；纯 `git clone` 不会带 → 按下面重建。

| 子目录 | 是什么 | 谁用 | 怎么重建 |
|---|---|---|---|
| `models/` | Qwen/Qwen3-Embedding-0.6B 的 HuggingFace 缓存（~1.2GB），结构 `hub/models--Qwen--…/` | `lib/embed.py`（把 `HF_HOME` 钉到这里；首次调用按需下载） | 删掉后首次跑检索/嵌入会自动重下 |
| `novnc/` | noVNC 1.4.0 网页 VNC 客户端（远程看屏前端，带手机双指缩放） | `pipeline/remote_view.sh`（`NOVNC_WEB`） | 重新下载 noVNC 1.4.0 解包到此；缺失时 remote_view.sh 回退发行版 `/usr/share/novnc` |

> 约定（2026-06-20 定）：**比较大的外部依赖统一进 `dependencies/`**，别再散落在模块内（原先模型在 `pipeline/retrieve/models/`、noVNC 在 `vendor/`，已合并到这里）。
