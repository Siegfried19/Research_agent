// Telegram notification + simple two-way control for the pipeline.
// Config: config/telegram.json (gitignored) = { "token": "...", "chat_id": "..." }
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { ROOT } = require('./db');

const CFG = path.join(ROOT, 'config', 'telegram.json');

function load() {
  if (!fs.existsSync(CFG)) return null;
  try { return JSON.parse(fs.readFileSync(CFG, 'utf8')); } catch { return null; }
}

const api = (token, method) => `https://api.telegram.org/bot${token}/${method}`;

// Send a message. No-ops (logs to stdout) if Telegram isn't configured yet.
async function notify(text) {
  const c = load();
  if (!c || !c.token || !c.chat_id) { console.log('[notify:offline]', text); return false; }
  try {
    const res = await fetch(api(c.token, 'sendMessage'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: c.chat_id, text }),
    });
    return res.ok;
  } catch (e) { console.log('[notify:error]', e.message, '::', text); return false; }
}

// Helper for setup: read the chat id of whoever last messaged the bot.
async function fetchChatId(token) {
  const t = token || (load() || {}).token;
  if (!t) throw new Error('no token');
  const res = await fetch(api(t, 'getUpdates'));
  const d = await res.json();
  const msgs = (d.result || []).map((u) => u.message).filter(Boolean);
  const last = msgs[msgs.length - 1];
  return last && last.chat ? { chat_id: last.chat.id, from: last.chat.username || last.chat.first_name } : null;
}

// Block until the user sends a message whose text matches `keyword` (case-insensitive
// substring), e.g. "go" / "done" to resume after they handle a Duo prompt.
async function waitForReply(keyword, { timeoutMs = 600000, pollMs = 3000 } = {}) {
  const c = load();
  if (!c || !c.token) return false;
  let offset = 0;
  const deadline = Date.now() + timeoutMs;
  // skip backlog: start from latest update id
  try {
    const init = await (await fetch(api(c.token, 'getUpdates'))).json();
    const ids = (init.result || []).map((u) => u.update_id);
    if (ids.length) offset = Math.max(...ids) + 1;
  } catch {}
  while (Date.now() < deadline) {
    try {
      const res = await fetch(api(c.token, 'getUpdates') + `?offset=${offset}&timeout=20`);
      const d = await res.json();
      for (const u of d.result || []) {
        offset = u.update_id + 1;
        const txt = (u.message && u.message.text) || '';
        if (txt.toLowerCase().includes(keyword.toLowerCase())) return true;
      }
    } catch { await new Promise((r) => setTimeout(r, pollMs)); }
  }
  return false;
}

module.exports = { notify, fetchChatId, waitForReply, CFG };
