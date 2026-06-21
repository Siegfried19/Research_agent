<div align="center">

# 📚 Research Agent · 研究论文流水线

**从一段研究思路，到一座可检索、自核查的中文论文知识库。**
*From a research idea to a searchable, self-verifying knowledge base of papers.*

[![python](https://img.shields.io/badge/python-3.12-blue.svg)](environment.yml)
[![engine](https://img.shields.io/badge/engine-claude%20%2B%20codex-8A2BE2.svg)](#-特色)
[![storage](https://img.shields.io/badge/storage-SQLite-003B57.svg)](data-base/)
[![status](https://img.shields.io/badge/status-running%20weekly-success.svg)](#-todo)

</div>

---

给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇用 AI 读完写**中文**结构化总结 → 换个模型再交叉核查一遍 → 存进可检索的知识库。每周增量跑一次，库就自己长大。

> *Give it a research idea; it discovers papers, fetches full text, writes structured Chinese summaries, cross-checks them with a second model, and grows a searchable knowledge base — run it weekly and the library builds itself.*

```bash
python3 pipeline/run.py <topic-id> auto
```

---

## ✨ 特色

- **🎯 按相关性选篇，不按引用量** —— 用 AI 给每篇命中打相关性分，避免"高引但跑题"的论文被排序顶上来。
- **🇨🇳 中文结构化总结** —— AI 直读 PDF，写三段要点 + 一段批判性的"局限与我的质疑"；总结**带版本**，结合新论文可迭代更新。
- **✅ 跨模型自核查** —— 写完的总结换**另一个模型**交叉核查幻觉；问题大的整篇从原文重做，而不是打补丁。
- **📥 全文四级降级取** —— 开放获取 → 规则兜底 → AI 猎源 → 图书馆代理付费墙，一层拿不到就降到下一层。
- **🔎 一座会关联的库** —— SQLite + 库内引用图 + 检索接口；论文质量标记持续跟随，用的时候不会忘了它是什么。
- **💸 走订阅、不花 API 钱** —— 打分/总结/核查全走本机 CLI（Claude + Codex）无头模式；幂等，撞限流重跑即可。
- **🤖 agent 优先** —— 让 AI 负责判断与编排，脚本只管确定性的力气活（下载、入库、核查），人负责设计流程和调 prompt。

---

## 🧩 流水线

```
discover → score → fetch → summarize → verify
  搜       选篇      取全文     写中文       换模型再校
```

五个模块各管一段，靠数据库状态机解耦：**find**（搜+选篇）· **fetch**（取全文）· **summarize**（写总结）· **verify**（核查）· **retrieve**（检索出口）。

新建主题只需写一个 `topics/<id>/topic.json`（研究思路 + 检索词），剩下交给 `run auto`。
架构全貌见 [`claude-memory/ARCHITECTURE.md`](claude-memory/ARCHITECTURE.md)。

---

## ✅ TODO

- [x] 论文自动发现 → 取全文 → 中文总结 → 跨模型核查（核心流水线已建成）
- [x] 每周增量跑、总结版本化、质量分档标记、Telegram 通知
- [x] SQLite 知识库 + 引用图 + 检索接口（FTS + 向量混合召回）
- [ ] 合成知识层：跨论文的综述与对比
- [ ] 引用图扩展与可视化
- [ ] idea → 论文稿全流程打通（与写作工具串起来，终极验收）

---

<div align="center">
<sub>中文优先 · 走订阅不花 API 钱 · 自核查 · 每周自动长大</sub>
</div>
