# SESSION 2026-06-16 — summarize+verify 改造的参考调研(收尾)

> 目标:改造 summarize+verify,治"张冠李戴幻觉"+"summarize prompt 不够好"。
> 本会话=**逐个过完 4 个重点参考 + 拍板架构**。**未动任何生产代码。**

## 干了什么
1. **逐个过完 4 个参考**,把"我们要借的"落到新文件 **`ref/TO-BORROW.md`**(取用清单,跟描述性的 REFS-OVERVIEW 分开):
   - ① DeepPaperNote:接地+证据四分(note_plan)/接地门脚本/7问。
   - ② claude-scholar:Evidence-gated → claim strength 四档 / allowed-forbidden 措辞 / source trust 分级(已拍板要借)。
   - ③ ARS:借**两个写作侧文件**(anti_leakage 知识隔离 + writing_quality 反AI腔),**非** deep-research 13-agent 本体;补 3 条(vibe-citing/魔鬼代言人/灰区=FAIL→unverifiable 分类型)。
   - ④ paper-qa:A组现用(图表防误配/I-cannot-answer/引文加引号);B组(闭集 citation key)留给出口②③ RAG。
2. **拍板架构=单 agent 模式**(模式1):一个 agent 多步 + 确定性脚本(接地门)+ 外层 Codex(写≠查)。依据:真正读单篇的①②④全单agent,唯一多agent的③干的是整篇论文大活;借的全部装得进单agent。处理一篇的 6 步全流程见 `ref/TO-BORROW.md` ★落地决定节。
3. **支线**:把 claude-scholar 的 `planning-with-files` 抽成独立库 **`~/Projects/agent-skills`**(复制式 install→`~/.claude/skills/`,远端待用户 push)。见记忆 [[agent-skills-repo]]。

## 记忆落点
- `ref/TO-BORROW.md` — ★ 取用清单(新对话先读这个)。
- `ref/REFS-OVERVIEW.md` — 描述性总览(claude-scholar 节补了 Evidence-gated+planning-with-files)。
- 跨会话记忆 `prompt-improvement-reference-study.md` — 四参考细读 + 单agent拍板。
- 跨会话记忆 `agent-skills-repo.md` — 新建的个人 skill 库。

## 下一步(新对话接)
出**正式落地方案**:写单篇总结 skill(单agent多步:知识隔离→note_plan+claim strength→接地门脚本→写(引文加引号/不夸)→自检(反AI腔中文词表/7问))+ 改 `summarize_auto.py` 每格调它 + `verify_summaries.py` 加 `unverifiable` 档(按论断类型分政策)+ 反AI腔英文词表本地化。待拍板小取舍:7问只进summarize还是也进verify;接地门对"中文总结→英文PDF"怎么定位出处。
