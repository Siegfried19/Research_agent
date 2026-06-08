export const meta = {
  name: 'relevance-score',
  description: 'Score discovery candidates for relevance to a research idea, in parallel batches',
  phases: [{ title: 'Score', detail: 'one agent per batch of candidates' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const idea = A.idea
const file = A.file            // path to candidates.json
const outDir = A.outDir        // dir to write batch_<start>.json
const total = A.total
const batchSize = A.batchSize || 10
if (!idea || !file || !outDir || !total) throw new Error('score.workflow: missing args idea/file/outDir/total')

const SCHEMA = {
  type: 'object',
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          relevance: { type: 'number', description: '0-100 relevance to the research idea' },
          reason: { type: 'string', description: '一句话中文理由' },
          edge_insight: { type: 'boolean', description: 'true if low-relevance but offers an unusual/valuable angle worth keeping' },
        },
        required: ['id', 'relevance', 'reason', 'edge_insight'],
      },
    },
  },
  required: ['scores'],
}

const ranges = []
for (let s = 0; s < total; s += batchSize) ranges.push([s, Math.min(s + batchSize, total)])

phase('Score')
const results = await parallel(ranges.map(([start, end]) => async () => {
  const prompt = `你在为一个学术研究流水线做"相关性打分"。研究思路如下：

"""${idea}"""

步骤：
1. 用 Read 工具读取文件 ${file}（JSON）。取其中 candidates 数组的下标 [${start}, ${end}) 这一段（共 ${end - start} 篇）。
2. 对每一篇，依据其 title + abstract，判断它对上述研究思路的相关性，打 0-100 分：
   - 90-100：直接命中（用 RL/模仿学习训练数字人/虚拟人/具身体/仿真角色与环境交互、全身运动控制等）
   - 60-89：强相关（物理仿真角色动画、humanoid 控制、具身智能体决策等）
   - 30-59：弱相关（沾边的 RL/动画/机器人但不针对"数字人与环境交互"）
   - 0-29：基本跑题（如纯 VR 体验、metaverse 综述、质性研究方法等）
3. reason 用一句中文说明为什么给这个分。
4. edge_insight：若某篇相关性不高(<60)但提供了不寻常、可能启发新思路的视角，标 true（你说过边角文章也要保留）。
5. 用 StructuredOutput 返回 scores 数组（每篇一项：id, relevance, reason, edge_insight）。
6. 同时用 Write 工具把同样的 JSON 数组写到 ${outDir}/batch_${start}.json（内容就是 scores 数组本身）。

注意：id 必须原样使用文件里每篇的 id 字段，不要改写。`
  const r = await agent(prompt, { label: `score:${start}-${end}`, phase: 'Score', schema: SCHEMA })
  return r && r.scores ? r.scores.length : 0
}))

const scored = results.filter((x) => typeof x === 'number').reduce((a, b) => a + b, 0)
log(`scored ${scored}/${total} candidates across ${ranges.length} batches`)
return { scored, batches: ranges.length }
