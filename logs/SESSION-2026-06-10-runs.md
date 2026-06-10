# SESSION 2026-06-10 — 放量跑两主题 + tierb 适配 + 手机过验证（远程看屏）

> 本文件记录"运行+抓取基建"这条会话线。同日另一实例在做质量评价体系/Codex 评审团（见 `SESSION-2026-06-10.md`）。DB/store 共享，互不冲突。

## 干了什么（按时间序）

### ① topic1 放量到 100（rl-digital-human-interaction）
- target 40→100，`run.py auto`。漏斗：raw 1560→去重 1158→池 200→增量入库 +95=**129 篇**。
- 全文：OA 直下 68 + recover 免费兜底 12 + tierb 付费墙 15 = **95/95 零丢失**；总结 95 篇 0 失败。
- **端到端实跑验证 tierb（待办#1 关闭）**：11/15 首轮成功，人工只点 1 次(ScienceDirect Turnstile)。

### ② tierb findPdfUrl 跨出版商适配
- 首轮 4 篇失败="landing 无 PDF 链接"，全是 IEEE/DSpace → 加适配：
  - **IEEE Xplore**：SPA 抓不到 DOM 链，改从 URL 提取 document 号构造 `stampPDF/getPDF.jsp?arnumber=`。
  - **DSpace 机构库**：选择器加 `a[href*="/bitstream"]`、`.pdf?` 带参链接。
  - **SPA 重试**：首轮没找到等 5s 再试一轮。
- 重跑 4 篇 → **4/4 成功**（IEEE×3 + NTU 学位论文），且这次 NYU 会话有效**没弹 Duo**。

### ③ topic2 新建并放量（rl-general-toolbox）
- 用户研究思路="RL 训练训不出来,要 reward 设计/算法工具箱/CBF 安全增强"。
- 我生成 14 组检索词（含 CBF、safe RL、TD3/SAC 改进、model-based、横评）→ 用户过目确认。
- 命名几经讨论定为 **`rl-general-toolbox`**（"RL 通用工具箱+诊断箱",对上未来 RAG 计划）。target=100,窗口12年。
- 漏斗：raw **3407**→去重 2269→池 200→首跑入库 **100 篇**（质量闸门:block0/flagout3/suspect1）。
- 全文：OA 62 + recover 10 + tierb 14 ；**8 篇与 topic1 重叠直接复用总结**（全局库设计生效）。

### ④ topic2 tierb 6 篇失败的修复（recover_oa + Wiley 适配）
- 诊断：6 篇里 **5 篇本该免费却漏到 tierb**（title-only/arxiv），仅 1 篇真付费墙(Wiley)。
- **根因=arXiv 取 PDF 的 bug**：`recover_oa` 旧逻辑 strip 掉版本号 → 裸 `/pdf/<id>` 个别论文 404（如 2211.15205 bare 和 v2 都 404、只有 v1 能下）。
  - 修：`arxiv_pdf_candidates()` **枚举** bare+v1..v最新,谁是真 %PDF 用谁；标题反查保留版本号。
- **Wiley 适配**：`/doi/pdf/` 是 HTML 拦截页 → `find_pdf_url` 特判 wiley 直返 `/doi/pdfdirect/{doi}?download=true`。
- 手动定位 "What Matters for On-Policy..."=arXiv `2006.05990`（发表改了标题,反查不上）。
- 结论：CIM/Regularization Matters/What Matters/Wiley 4 篇可救；PPG Reloaded/Lazy Agents 无免费版,留 pdf_failed。
- **执行待 topic2 sum 跑完**（避免抢写库）→ 给 What Matters 补 arxiv id → recover → tierb(Wiley) → worklist→sum→finalize。

### ⑤ 手机过验证：远程看屏（Tailscale + noVNC）★本会话主交付
- 需求：用户不想每次走回电脑点 Cloudflare/Duo,想**手机点**。
- 机制：验证必须点在机器那个真实 Chrome 上（cf_clearance 绑浏览器指纹+IP）,所以方案=让手机**远程看到并点到**机器的 `:1`。
- 数据流：手机浏览器 ⇄ Tailscale(WireGuard 加密私网) ⇄ websockify(托管 noVNC 网页+翻译 ws→VNC) ⇄ x11vnc(:1) ⇄ Chrome。
- 安全：**x11vnc 只听 localhost**(原始 VNC 不上网络)；唯一对外的 websockify **绑 Tailscale IP 100.83.75.76:6080**；VNC 密码；**不开 Funnel**(永不上公网)。残余风险仅"MS 账号被盗",用户有 2FA。
- 落地：
  - `pipeline/remote_view.sh`：幂等启动 x11vnc+websockify,首跑生成随机 VNC 密码,打印手机 URL。密钥 `config/x11vnc.{pass,plain}` gitignored。
  - `fetch_tierb.py`：加 `ensure_remote_view()`,tierb 开跑预热并把链接放进"开跑通知"；`wait_human` 弹验证时 Telegram 消息带 noVNC 链接。
  - URL 形如 `http://100.83.75.76:6080/vnc.html?...&autoconnect=true&resize=scale&password=...`,手机点开即自适应显示、直接点验证。
- 验证：服务起、端口绑定正确(5901 localhost / 6080 tailscale)、vnc.html HTTP200、幂等不起重复、ensure_remote_view 缓存正常；已发测试链接到 Telegram **待用户手机实测**。

## 待办（这条线）
1. **用户手机实测远程看屏链接**（能看到屏幕即全链路通）。
2. topic2 sum 跑完 → 执行④的 4 篇救回+总结入库 → topic2 最终报告。
3. 本会话改动未 commit（另一实例也在改 fetch_tierb.py/CLAUDE.md,等两条线都停一起提交）。
4. 解锁：现有 2 主题 → 可跑 `cross_topic.py`（待办#4）。
