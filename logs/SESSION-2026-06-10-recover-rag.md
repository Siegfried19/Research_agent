# SESSION 2026-06-10 — 救回失败篇 + 下载兜底升级 + Chrome 生命周期 + RAG①(ask.py)

> 本文件记录"下载基建 + RAG"这条会话线。同日并行的还有:质量核查/修正线(verify/correct,见
> SESSION-2026-06-10.md)和放量运行线(SESSION-2026-06-10-runs.md)。

## 干了什么(按时间序)

### ① 救回 topic2 最后 2 篇 pdf_failed → 100/100
- PPG Reloaded / Lazy Agents,昨晚结论"无免费版"是错的:都是 ICML 2023,PMLR 官网免费。
- 根因:recover 渠道(Unpaywall 要 DOI + arXiv 反查)覆盖不到 PMLR 这类会议自营 OA 站。
- 手动拉 PDF→pdftotext→落库,走标准 worklist→sum→finalize 补总结。

### ② 由此固化两层新兜底(下载链三级→四级,均已实测)
- `recover_oa.py` + **dblp-oa 渠道**:DBLP 标题反查(全等才认)→ee 落在 PMLR/ACL Anthology/
  OpenReview 就构造 PDF 直链。误伤测试:不存在的标题/ee 在别处的论文均正确返回 None。
- 新阶段 **hunt**(`recover_agent.py`,插在 recover 与 tierb 之间):规则渠道全空的论文,
  无头 claude -p 开 WebSearch/WebFetch 联网找合法免费 PDF(prompt 明令禁盗版源);agent 只给
  链接,下载/%PDF 校验/落库全是脚本。临时库 e2e:agent 自己搜到 PMLR,10MB 下载校验入库。
- `lib/claude.py`:run_claude 加 tools 参数(--allowedTools)。

### ③ tierb Chrome"越开越多"根治(照 Stock_agent 补齐缺的后半截)
- 病根:fetch_tierb 只抄了 ensure_chrome(启动),没有关闭逻辑。
- 修法:跑前 flock 独占(锁=UDD/scrape.lock,共用实例的任务天然同一把锁)→ finally **无条件**
  pkill -f "user-data-dir=<UDD>" 整关(独立目录绝不误伤日常 Chrome;复用来的残留也关)。
- 副产物:每次 fresh launch→PDF 下载 pref 必生效→方法 B 始终可用。
- 残余风险:Stock_agent 的锁还在它项目本地,两项目极端撞车时 tierb 收尾会关掉它在用的实例。

### ④ RAG 第一步落地:`ask.py`(FTS5 库内问答)
- 索引=独立 `db/fts.sqlite`(gitignored 可重建):fts_sum(trigram,标题+摘要+中文总结)+
  fts_text(porter,英文全文),mtime 增量,221 篇唯一论文。
- 查询:英文取词;中文按停用词切段,≤4 字精确短语、长段拆滑窗 trigram、2 字词 instr 全扫兜底。
  **坑:FTS5 虚拟表上 LIKE 静默返回 0 行,必须用 instr()**。
- 出口认 quality_tier(硬约束):suspect 减半+⚠️标注;flag 注"预印本"。
- `--answer`:claude -p 综合前 5 命中,带 [编号] 引用,实测会老实说"库里没有"不编造。

### ⑤ 失误与发现
- 失误:误解"已经在抽检"又重复跑了一轮 verify,与核查线撞车(残留影响零,浪费~23 次 Codex 调用)。
  教训已记:**起长任务前先看 run.log 最近条目,确认没有别的实例在干同一件事**。
- 发现:Bipedal Robots 以两个 id 重复入库(`..._Bipedal_Robots`/`..._2`,跨主题 merge 没合上),待去重。
- 回顾确认:ref/academic-research-skills(ARS)的 deep-research 默认联网现搜,不基于本地库;但其
  corpus-first 模式可吃我们导出的 literature_corpus[],与 RAG 计划有接口(只记录,未动手)。

## 状态
- 两主题 229 篇全部 summarized,零积压。hunt 阶段进了 run auto。ask.py 可用。
- 前半段(①②③)已由并行实例在 13:55 commit aa3ea8b;本文件与 RAG①(④)单独一笔提交。
