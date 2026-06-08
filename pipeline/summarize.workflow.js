export const meta = {
  name: 'summarize-papers',
  description: 'One agent per paper: read full text, write a Chinese structured summary md',
  phases: [{ title: 'Summarize', detail: 'one sub-agent per paper' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const file = A.file            // path to summarize_worklist.json
const total = A.total
if (!file || !total) throw new Error('summarize.workflow: missing args file/total')

const idxs = Array.from({ length: total }, (_, i) => i)

phase('Summarize')
const results = await parallel(idxs.map((i) => async () => {
  const prompt = `你是论文精读员。请为工作清单中的第 ${i} 篇论文写一份**中文**结构化总结。

步骤：
1. 用 Read 读取 ${file}，取 work 数组下标 ${i} 的条目（含 id/title/authors/year/venue/citation_count/doi/text_path/pdf_path/summary_path 等）。
2. 用 Read 读取该论文全文：优先读 text_path；若 text_path 为 null 或内容过短，则读 pdf_path（Read 能直接读 PDF）。务必基于**正文**总结，不要只看标题。
3. 按下面的模板写总结，**三段固定置顶**，全文中文（论文是英文/日语也要读懂后用中文写）：

---
paper_id: <条目的 id 原样>
version: 1
based_on: []
created_at: <当前日期 2026-06-07>
note: 首次总结
---

# <论文标题>
> 作者 · 年份 · 期刊/会议 · 引用数 · DOI

## 一句话
（一句话概括这篇论文做了什么）

## 解决了什么问题
（这篇论文针对的具体问题/痛点）

## 用什么方法解决的
（核心方法/模型/思路，讲清楚怎么做的）

---

## 动机 & 背景
## 方法细节
（展开方法：架构、算法、关键设计选择）
## 数据集 & 实验设置
（用了什么数据/仿真环境/评测指标；没有就写"无/不适用"）
## 主要结果 & 结论
## 核心贡献
（bullet 列点）
## 局限与我的质疑
（既写作者自述局限，也写**你自己的批判**：方法是否站得住、实验是否充分、结论是否被过度解读、与"RL训练数字人与环境交互"这一主题相比有何不足。至少 3 条。）

4. 用 Write 把这份 md 写到该条目的 summary_path（先确保其目录存在；Write 会自动建目录）。
5. 完成后只需返回一行："done <id>"。

要求：忠实于原文、不要编造数字；方法和结果要具体；质疑要有实质内容而非套话。`
  const r = await agent(prompt, { label: `sum:${i}`, phase: 'Summarize' })
  return r ? 1 : 0
}))

const done = results.filter((x) => x === 1).length
log(`summarized ${done}/${total}`)
return { done, total }
