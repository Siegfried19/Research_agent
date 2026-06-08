# 研究论文流水线

给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇一个子 agent 写中文总结 → 存入 SQLite 库。
支持每周增量跑、总结版本化更新、跨主题比较。

## 快速看产出（建议从这里开始审）

- **样张总结**：`store/summaries/PADL_Language-Directed.../v1.md` 等 —— 中文，三段置顶 + 「局限与我的质疑」批判段
- **版本化更新示例**：`store/summaries/Synthesizing_Diverse_Human_Motions_in_3D_Indoor_Scenes/`（v1 + v2 共存，v2 结合相关论文更新）
- **主题视图**：`topics/rl-digital-human-interaction/topic.md` —— 按相关性排序的命中清单 + 相关性理由 + 库内引用关系
- **数据库**：`db/papers.sqlite`

## 数据库（5 张表）

| 表 | 作用 |
|---|---|
| `papers` | 全局论文库，一篇一行（主键＝规范化 DOI；`slug`＝标题文件名；`status`＝discovered/pdf_downloaded/pdf_failed/summarized）|
| `topics` | 研究主题（思路 + 生成的检索词）|
| `paper_topic` | 论文×主题（相关性分 + 理由 + 命中检索词 + rank）|
| `summary_versions` | 总结版本历史（version / path / based_on / note）|
| `citations` | 库内论文相互引用边 |

查询示例：
```bash
node --experimental-sqlite -e "const{open}=require('./pipeline/lib/db');const db=open();
console.log(db.prepare('SELECT title,relevance FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id WHERE pt.topic_id=? ORDER BY rank LIMIT 10').all('rl-digital-human-interaction'))"
```

## 跑一个主题（一键编排）

1. 建 `topics/<id>/topic.json`（含 id/title/idea/queries/window_years/target）。检索词由 Claude 按研究思路生成。
2. 按阶段跑（两个 agent-workflow 步骤由 Claude 在中间调用）：

```bash
bash pipeline/run.sh <id> discover     # 多源搜 → candidates.json
bash pipeline/run.sh <id> scoreargs    # 清 scores、打印评分 workflow 的 args
#   → Claude 跑 score.workflow.js（相关性打分，滤掉跑题高引论文）
bash pipeline/run.sh <id> commit       # 选篇写库（首跑 TopN / 增量追加）
bash pipeline/run.sh <id> fetch        # 下载 OA 全文（含 arXiv 回退）
bash pipeline/run.sh <id> worklist
bash pipeline/run.sh <id> sumargs      # 打印总结 workflow 的 args
#   → Claude 跑 summarize.workflow.js（每篇一个 agent 写 v1.md）
bash pipeline/run.sh <id> finalize     # 回写库 + 渲染 topic.md
```

## 其它操作

```bash
# 增量跑：同一主题再跑一遍上面的流程，已总结的自动跳过，只加新命中
node --experimental-sqlite pipeline/recover_oa.js <id>              # 免费补全没下到的全文（Unpaywall+arXiv，零登录）
node --experimental-sqlite pipeline/suggest_updates.js <id>          # (5b) 建议哪些老总结该更新
node --experimental-sqlite pipeline/prepare_update.js <paperId>      # (5a) 备更新（相关论文默认取引用邻居）
#   → Claude 跑 update.workflow.js → 生成 vN+1（旧版保留）
node --experimental-sqlite pipeline/register_updates.js
node --experimental-sqlite pipeline/cross_topic.js                   # (6) 跨主题共享论文 + 引用桥（需≥2主题）
```

## 设计要点 / 已知限制

- **不用 Google Scholar 批量**（无 API、强反爬）；用 OpenAlex + Semantic Scholar + arXiv + PubMed，按 DOI 去重。
- **选篇靠 agent 相关性打分**，不靠 API 排序（API 会把高引但跑题的论文顶上来）。
- **付费墙（Tier B）暂未接**：非 OA / 403 的论文走 opencli + 你登录的 Chrome 图书馆代理，后续再做。当前只吃 OA 免费源。
- Semantic Scholar 无 key 时会 429（已优雅降级）；批量下载对出版商要克制，别刷崩你学校访问。
- 所有 node 脚本需 `--experimental-sqlite`。

详细决策记录见会话记忆 `research-paper-pipeline.md`。
