# 质量评价体系（横切子系统）

> 给 AI agent 读的设计长文。**以代码为准**：核心逻辑在 `pipeline/lib/quality.py`，名单在 `config/quality/`。

## 是什么 + 设计哲学

纯代码**硬信号**（不用 LLM、不调网，名单全等匹配），给每篇论文贴一个可信度档位，
防水刊 / 撤稿 / 预印本污染下游。

核心哲学（用户定）：**能标记就不一刀切删**——污染不发生在「存进去」，而发生在「用的时候忘了它是什么」。
所以除最确凿的死刑信号外，一律**带标记入库**；verdict 持久化在
`papers.quality_tier` / `papers.quality_signals`，**每个下游出口都认这个标记**。

入口：`quality.assess(paper) -> {"tier": ..., "signals": [...]}`。
`paper` 是 dict，认 `doi / venue / publisher / is_retracted / is_in_doaj / sources`
任意子集（candidates.json 条目和 papers 表行都能喂；缺键=未知）。
档位：`block` / `suspect` / `trusted` / `flag` / `ok`（五值，`ok`=啥信号都没命中）。

## 四档（命中什么 + 怎么处置）

判定顺序（见 `assess`）：先算 trusted 信号 → **block（直接返回）** → suspect（白名单 venue 免疫）
→ trusted → flag/ok。

- **block**（死刑，**永不入库**）：`is_retracted`（OpenAlex 撤稿）/ DOI 前缀命中
  `doi_prefix_blocklist.txt`（亲手确认过的水刊）。
  - discover 阶段直接丢弃（`discover.py`：tier==block 不入池）；
  - commit 阶段双保险再挡一次（`commit.py`：tier==block continue）。

- **suspect**（**入库带标记**）：掠盗刊 / 出版商**名单命中**（`predatory_journals.txt`+
  `local_blocklist.txt` 命中 venue，或 `predatory_publishers.txt` 命中 publisher）。
  Beall's 有争议条目、全等匹配也可能偶撞，所以不删只标。**白名单 venue 对此免疫**。
  - commit：需 `relevance >= flag_min_relevance`（默认 **45**，`config.json`）才入选，否则 OUT；
  - summarize：自动切**质疑模式**（注入批判指令：开头警示行、写「作者声称」、
    「局限与我的质疑」≥5 条、主动找硬伤）；
  - render：topic.md 表格标 ⚠️ + 单列「⚠️ 低可信来源」节；
  - retrieve（ask）：答案里 ⚠️ 标注「低可信来源（掠盗刊嫌疑，引用需核实）」（**只标不删**）。

- **flag**（入库带标记，门槛同 suspect）：纯预印本 / 无 venue。
  判定见 `PREPRINT_VENUES`（arxiv/biorxiv/medrxiv/ssrn/preprints/research square/techrxiv）
  或 `sources=={"arxiv"}`，且 venue 无标注。
  - ⚠️ **有正式 DOI（非 `10.48550` 的 arXiv 前缀）的不算纯预印本**——OpenAlex 常把已发表论文
    的 primary_location 指到 arXiv 版、venue 显示 arXiv，但其实过了同行评审。
  - commit：同 suspect，需 `relevance >= flag_min_relevance`；
  - summarize：总结注一句「预印本/未经同行评审，对未验证结论保持保留」；
  - retrieve：答案标「(预印本，未同行评审)」。

- **trusted**（免疫名单误杀）：venue 命中 `venue_whitelist.txt`（含子串匹配）
  或 `is_in_doaj`（DOAJ 收录）。让白名单 venue 不被名单误判成 suspect。

## 信号来源 / 名单（`config/quality/`，纯文本，可手工编辑追加；`#` 后为注释）

- `predatory_journals.txt`（~1310 行）/ `predatory_publishers.txt`（~1162 行）：
  **Beall's 衍生 stop-predatory-journals**，**2017 年停更**。`*_raw.csv` 是原始抓取。
- `local_blocklist.txt`：新水刊**手工补**（停更名单覆盖不到的，与 journals 合并参与匹配）。
- `doi_prefix_blocklist.txt`：水刊 DOI 前缀 → block（如 IJISRT=`10.38124`）。
- `venue_whitelist.txt`：可信 venue → trusted，并对 suspect 名单免疫。
- DOAJ：不是本地文件，来自论文元数据 `is_in_doaj`（OpenAlex 给，见 `lib/sources.py`）。

匹配做了归一化（`norm_name`：小写、去标点、压空格、去开头 the）+ 全等/子串。

## 各出口怎么认标记

| 出口 | 行为 |
|---|---|
| `find/discover.py` | block 直接丢弃，suspect 入池打日志（第一道闸） |
| `find/commit.py` | block 双保险再挡；flag/suspect 需 relevance≥flag_min；suspect 标「质疑模式入库」（第二道闸） |
| `summarize/summarize_auto.py` | suspect→质疑模式批判指令；flag→注「未经同行评审」 |
| `summarize/render_topic.py` | suspect 表格 ⚠️ + 单列「低可信来源」节 |
| `ask.py` / `retrieve/answer.py` | suspect/flag 在答案里 ⚠️ 标注（**只标不过滤**）；完整 tier 进 `--json` 供外部 agent 自决 |

> 注：retrieve 当前是「标注」而非 CLAUDE.md 早期设想的「默认过滤/降权」——**只标不删，与全系统哲学一致**。
> （CLAUDE.md「默认过滤/降权」措辞偏旧，实现以 `answer.py` 为准。）

## 回溯审计

`python3 pipeline/tools/audit_quality.py <id>`：按 DOI 拉 **OpenAlex 最新元数据**
（is_retracted / is_in_doaj / publisher）重核已入库论文 → 出报告 `topics/<id>/quality_audit.md`
+ **verdict 回写 DB**（dry-run 也回写 quality_tier/quality_signals）。
`--apply` 只删 block 级 + 重算 rank。
（实测 2026-06-10 跑 129 篇：block=0 / suspect=0 / flag=34 全是真预印本 / trusted=36 / ok=59。）

## 关键文件

- 逻辑：`pipeline/lib/quality.py`（`assess` / `norm_name` / `_lists`）
- 名单：`config/quality/*.txt`
- 阈值：`pipeline/config.json` → `quality.flag_min_relevance`（默认 45）
- 出口：`find/discover.py`、`find/commit.py`、`summarize/{summarize_auto,render_topic}.py`、
  `ask.py`、`retrieve/answer.py`、回溯 `tools/audit_quality.py`
