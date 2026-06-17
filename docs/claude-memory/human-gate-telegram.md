---
name: human-gate-telegram
description: 用户偏好——需要他拍板的人工关卡(如打分锚点挑选/确认)，除了终端也推一份到 Telegram，两边都能审
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ea62bf0a-79ea-433d-8eeb-c29d95f72f4e
---

2026-06-17：设计打分漂移修法的"锚点冷启动"时，用户说挑出的 3 张候选样卷"建议也在 telegram 上发给我，这样我两边都能看"。

**Why**：用户不总在机器旁；要他拍板的决策推到手机能随时审，不卡流程。

**How to apply**：凡是"要用户过目/确认"或"该让他知道脚本替他做了什么决定"的环节，除了终端,也用 `notify()` 推一份到 Telegram。这与 tierb 点验证用 TG 喊人同性质。
注:打分锚点这个具体案例**最终走向全自动**(用户后来定"没必要介入"),所以锚点不再是阻塞关卡——但自举挑完仍**非阻塞推 TG 告知**挑了哪三张(可事后改),正体现这条偏好"两边都能看"。见 [[score-drift-external-research]]。
