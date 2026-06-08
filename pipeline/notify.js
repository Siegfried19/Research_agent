// Telegram CLI: set up the bot config, grab chat id, and send test messages.
//   node pipeline/notify.js settoken <BOT_TOKEN>     # save token to config/telegram.json
//   node pipeline/notify.js chatid                   # read chat id (after you message the bot once)
//   node pipeline/notify.js test "hello"             # send a test message
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { ROOT } = require('./lib/db');
const { notify, fetchChatId, CFG } = require('./lib/notify');

function readCfg() { try { return JSON.parse(fs.readFileSync(CFG, 'utf8')); } catch { return {}; } }
function writeCfg(o) {
  fs.mkdirSync(path.dirname(CFG), { recursive: true });
  fs.writeFileSync(CFG, JSON.stringify(o, null, 2));
  fs.chmodSync(CFG, 0o600);
}

async function main() {
  const [cmd, arg] = process.argv.slice(2);
  if (cmd === 'settoken') {
    if (!arg) { console.error('usage: notify.js settoken <BOT_TOKEN>'); process.exit(1); }
    const c = readCfg(); c.token = arg.trim(); writeCfg(c);
    console.log('token saved to config/telegram.json (chmod 600). Now message your bot once, then run: notify.js chatid');
  } else if (cmd === 'chatid') {
    const found = await fetchChatId();
    if (!found) { console.log('no message found — send any message to your bot first, then retry'); return; }
    const c = readCfg(); c.chat_id = found.chat_id; writeCfg(c);
    console.log(`chat_id ${found.chat_id} (from ${found.from}) saved. Telegram ready.`);
  } else if (cmd === 'test') {
    const ok = await notify(arg || 'Research_agent: test ✅');
    console.log(ok ? 'sent' : 'not sent (check config/telegram.json)');
  } else {
    console.log('commands: settoken <token> | chatid | test "<msg>"');
  }
}
main().catch((e) => { console.error(e); process.exit(1); });
