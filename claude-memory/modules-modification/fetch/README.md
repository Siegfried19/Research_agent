# fetch — 四级取全文（定型设计）

把 commit 选中的论文拿到**全文 PDF**。PDF 是唯一原文来源——总结/核查都直读 `storage/sources/<slug>/paper.pdf`，**不再抽存 store/text 文本**（2026-06-16 移除）。
代码：`pipeline/fetch/`。Tier B 的运维步骤（换机器重建 Chrome/登录 NYU）见 `../../ops/`，本文只写设计与原理。

## 设计哲学：四级降级 + 撞墙就固化新渠道
按"越免费/越省事 → 越贵/越要人"分四级，前一级拿到 PDF 就不进下一级；每篇按 `source_topic.rank` 顺序处理、`status` 流转 `discovered → source_ready / source_failed`。

> **核心心法**（用户定）：**撞到一类拉不下来的，就固化一个新渠道**——recover_oa 的 host 适配、tierb 的 `find_pdf_url` 出版商分支，都是这么长出来的。一次性手动救一篇之后，把这一类沉淀成代码，下次自动覆盖。

1. **OA**（`fetch_oa.py`）：discover 标了 `is_oa=1` 且有 `oa_url` 的，直接下。带 arXiv 回退（`ext_ids.arxiv` 或 `id` 前缀 `arxiv:`，去版本号拼 `arxiv.org/pdf/<id>`）。
2. **recover**（`recover_oa.py`）：**无登录的规则免费兜底**，对缺 PDF 的篇按序试多个候选 URL，谁先是真 PDF 就用谁：
   - **arXiv by id**：枚举 bare + v1..v\<latest\>（arXiv 怪癖——bare 路径会 404，"最新版"也可能 404 而早期版能服务，所以全枚举让下载循环挑）。
   - **Unpaywall**：**repository/arXiv 托管优先、publisher 最后**（publisher 的 PDF 直链常 403）。这是修过的老 bug：旧代码先取 `best_oa_location`（多半 publisher）+ 只按完整标题精确配 arXiv（被 OpenAlex 截断的标题就漏）。
   - **arXiv by title**：标题归一化全等才认，保留版本后缀。
   - **dblp-oa**（会议自营 OA 站，2026-06-10 加）：DBLP 标题反查（全等才认）→ ee 落在 **PMLR / ACL Anthology / OpenReview** 就构造 PDF 直链。覆盖无 DOI、无 arXiv 的会议论文（如 ICML 在 PMLR）。
3. **hunt**（`recover_agent.py`）：**规则渠道全空才轮到它**。无头 `claude -p` 开 WebSearch/WebFetch 联网找**合法**免费 PDF 直链（作者主页/机构库/会议官网/preprint server；prompt 明令禁 Sci-Hub/LibGen 等盗版源与任何绕付费墙/需登录的链）。**agent 只给链接，下载/校验/落库全是脚本**——便宜的联网 agent 先于昂贵的浏览器+登录路。
   - **张冠李戴防线**：agent 可能给"真实有效但属于另一篇"的 PDF（%PDF 校验挡不住）→ 下载后 pdftotext 抽文本 + `title_matches` 核对，不匹配就删掉拒收（抽不出文本则放过，反正总结阶段无 PDF 会跳）。
4. **Tier B**（`fetch_tierb.py`，方法④）：最后才走付费墙。驱动**已登录的真实 Chrome**（经 opencli 桥）拉付费墙（NYU OpenAthens）或被 bot 防护的 OA（Cloudflare）。**唯一需要人**=遇 Cloudflare/Duo 验证时点一下（脚本暂停+Telegram 喊人，点掉后自动续）。幂等：已 `source_ready` 的跳过。

## Tier B 怎么抓、为什么这么抓
- **NYU 访问路径**：NYU 已弃 EZProxy 迁 **OpenAthens**，旧 `proxy.library.nyu.edu` 废。新路径 = `go.openathens.net/redirector/nyu.edu?url=<doi>`。
- **混合下载（B 优先 + A 兜底）**，两者都过 `%PDF` 头 + `pdfinfo` 页数校验：
  - **方法 B（优先）**：fresh launch 时改 profile pref（`always_open_pdf_externally=true` + 下载目录 `storage/dl_tmp`）使 PDF **直接下载**，盯目录等新的、稳定的 `.pdf`（无 `.crdownload` 伴随、size 稳定）→ 搬到 `storage/sources/<slug>/paper.pdf`。
  - **方法 A（兜底）**：B 在 ~20s 内没出文件（如在阅读器打开/pref 未生效）→ 页面内 `fetch(location.href,{credentials:'include'})` → `btoa`（8192 分块、同一次 eval）→ 分块读出 base64 → 落盘。
  - ⚠️ **B 只在 fetch_tierb 自己启动 Chrome 时才生效**（关着才能改 pref）；若连上的是已开着的 Chrome，则只用 A。
- **`find_pdf_url` 出版商适配的坑**（撞一类固化一个）：
  - **Wiley**：`/doi/pdf/` 是 HTML 拦截页 → 直返 `/doi/pdfdirect/{doi}?download=true`。
  - **IEEE Xplore**：SPA 抓不到 DOM 链 → 从 URL 取 document 号构造 `stampPDF/getPDF.jsp?arnumber=`。
  - **ACM**（dl.acm.org）：构造 `/doi/pdf/{doi}`，自动过 Cloudflare 无需登录。
  - **DSpace 机构库**：选择器加 `a[href*="/bitstream"]`、`.pdf?`。
  - **通用**：先认 `meta[name=citation_pdf_url]`，再扫一串 `<a>` 选择器；**SPA 首轮没找到等 5s 重试**（Xplore/DSpace7 可能还没渲染完）。
  - 现象：ScienceDirect/Elsevier 每篇都弹 Turnstile；ScienceDirect 的 pdfft 链会自动跳签名 S3。

## Chrome 生命周期（根治"越开越多"）
- **独立 user-data-dir**（2026-06-17）：`~/.config/google-chrome-scrape-nyu`，与 Stock_agent 的 `google-chrome-scrape` **物理隔离**（共用会三重冲突：收尾互相 pkill、Chrome 单实例/目录限制、flock 锁不互斥）。隔离后两项目可随便一起跑。可用 env `CHROME_USER_DATA_DIR` 覆盖。NYU OpenAthens 会话只登在该 profile 的 "Profile 2"。
- **flock 独占**（锁=`<UDD>/scrape.lock`）+ **finally 无条件 pkill** `-f "user-data-dir=<UDD>"` 整关：按独立目录匹配绝不误伤日常 Chrome，复用来的实例也关。副产物=每次 fresh launch → PDF pref 必生效 → 方法 B 始终可用。
- **profile 别名**靠 `detect_alias()` 自动认（从 `opencli profile list`），**别写死**（随机器变）。

## 失败兜底：报失败 + 手动挂 PDF（定稿 2026-06-21）
fetch 几乎不失败（生产库常年 `source_failed=0`），所以**不建诊断/分类 agent**，只留极简两步：
- **⑤ 报失败** `python3 pipeline/run.py <id> failed`：列出本主题没拿到全文的篇（`source_path IS NULL AND status IN ('source_failed','discovered')`），打印 `标题/id/slug/DOI/落地页`。只报"是哪篇"——失败类型不展示不入库（要查时由处理的 agent 临场看日志/元数据判）。全拿到则输出 ✅，平时零噪音。
- **⑥ 手动挂回库**（不写工具）：失败篇在 `sources`/`source_topic` 的行 find 阶段已 commit，所以"入库"只是拷 PDF 到 `storage/sources/<slug>/paper.pdf` + `UPDATE sources SET status='source_ready', source_path=...`（即 `fetch_oa.py` 末尾三行）。用户自己下好 PDF，叫 agent 现场用 SQL 挂上，再走 worklist→sum。
- 红线不变：**不接盗版源**；付费墙只走 NYU 合法订阅。

## facet（只在主题状态档，不入库）
每篇在本主题下的 find 子方向 facet 存在**主题状态档**（`topics/<id>/topic.json` 的 `facets` + `candidates.json` 每篇 `facet`），**不复制进数据库**——2026-06-21 撤回了曾加的 `source_topic.facet` 列（主题状态档是单一真相源，详见 STATE / `claude_log.md` 01:11 条）。`fetch` 对 facet 无感（仍按主题+rank 取 PDF）；retrieve 日后要按 facet 过滤就直接读主题状态档。详见 `../find/README.md`。

## 边界（不属于本模块）
- 选哪些篇下载（打分/选篇/资格闸）= **find** 模块；本模块只对已选中的篇取 PDF。
- 下载下来后写总结/核查 = **summarize / verify** 模块。
- 质量标记（block/suspect/flag）在 discover/commit 阶段定，本模块不判质量。
- 手机过验证的远程看屏（noVNC/x11vnc）已**封存**（MOTHBALLED 2026-06-10，默认关，见 STATE）。
