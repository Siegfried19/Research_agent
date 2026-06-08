// Tiny fetch wrapper: timeout, retries, polite delay. Uses global fetch (Node 18+).
'use strict';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getJSON(url, opts = {}) {
  return get(url, { ...opts, as: 'json' });
}
async function getText(url, opts = {}) {
  return get(url, { ...opts, as: 'text' });
}

async function get(url, opts = {}) {
  const {
    as = 'json',
    headers = {},
    timeout = 60000,
    retries = 2,
    retryDelay = 1500,
  } = opts;
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeout);
    try {
      const res = await fetch(url, {
        headers: { 'User-Agent': 'ResearchAgent/0.1', ...headers },
        signal: ctrl.signal,
        redirect: 'follow',
      });
      clearTimeout(t);
      if (res.status === 429 || res.status >= 500) {
        throw new Error(`HTTP ${res.status}`);
      }
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw Object.assign(new Error(`HTTP ${res.status} ${url}`), {
          status: res.status,
          body: body.slice(0, 300),
          fatal: res.status >= 400 && res.status < 500 && res.status !== 429,
        });
      }
      return as === 'json' ? await res.json() : await res.text();
    } catch (e) {
      clearTimeout(t);
      lastErr = e;
      if (e.fatal) break;
      if (attempt < retries) await sleep(retryDelay * (attempt + 1));
    }
  }
  throw lastErr;
}

module.exports = { get, getJSON, getText, sleep };
