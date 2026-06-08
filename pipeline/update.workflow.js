export const meta = {
  name: 'update-summaries',
  description: 'Re-summarize papers into a new version in light of related (often newer) work; keep old versions',
  phases: [{ title: 'Update', detail: 'one agent per paper, writes vN+1' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const file = A.file
const total = A.total
if (!file || !total) throw new Error('update.workflow: missing args file/total')

const idxs = Array.from({ length: total }, (_, i) => i)

phase('Update')
const results = await parallel(idxs.map((i) => async () => {
  const prompt = `你在做论文总结的"版本化更新"。读取 ${file}，取 work 数组下标 ${i} 的条目。

条目含：paperId, title, currentVersion, currentPath（当前最新版总结 md）, nextVersion, outPath（要写的新版路径）, related（一组相关论文，每个含 id/title/path 指向其总结 md）。

步骤：
1. 用 Read 读取 currentPath（这篇论文当前的总结）。
2. 用 Read 逐个读取 related 里每篇相关论文的总结（path）。这些通常是更新的、引用或被引用本文的工作。
3. 写一份**新版总结**（中文），保持原有结构与三段置顶模板（一句话/解决了什么问题/用什么方法解决的/动机/方法细节/数据集/结果/核心贡献/局限与我的质疑），但要：
   - 在内容中**整合相关工作的视角**：这篇论文在更广文献脉络中的位置、被后续工作如何延展/挑战/超越、其方法或结论在新证据下是否仍站得住。
   - 新增一节 \`## 在相关工作脉络中的更新\` —— 简述这次更新（对应条目的 nextVersion）参考了哪些相关论文、它们带来的新认识。
   - 保留并可深化"局限与我的质疑"。
   - frontmatter 写：version: <nextVersion>，based_on: [related 的 id 列表]，note: 一句话说明本次更新依据。
4. 用 Write 把新版写到 outPath。
5. 返回一行 "updated <paperId> -> v<nextVersion>"。

不要改写旧版文件；只新增新版。忠实于原文，不臆造。`
  const r = await agent(prompt, { label: `upd:${i}`, phase: 'Update' })
  return r ? 1 : 0
}))

const done = results.filter((x) => x === 1).length
log(`updated ${done}/${total}`)
return { done, total }
