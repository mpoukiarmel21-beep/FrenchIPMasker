// FrenchIPMasker - Background Service Worker
// Scrapes French proxies, tests them, applies via Chrome proxy API

const PROXY_SOURCES = [
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=FR&ssl=all&anonymity=all",
  "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
  "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
  "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt"
];

let pool = [];
let currentProxy = null;
let active = false;
let running = false;

// ─── Proxy Application ───────────────────────────────
function applyProxy(proxyStr) {
  if (!proxyStr) {
    chrome.proxy.settings.clear({ scope: 'regular' });
    currentProxy = null;
    return;
  }
  const [host, port] = proxyStr.split(':');
  chrome.proxy.settings.set({
    value: {
      mode: "fixed_servers",
      rules: {
        singleProxy: { scheme: "http", host: host, port: parseInt(port) }
      }
    },
    scope: 'regular'
  });
  currentProxy = proxyStr;
}

function removeProxy() {
  chrome.proxy.settings.clear({ scope: 'regular' });
  currentProxy = null;
}

// ─── Proxy Testing ────────────────────────────────────
async function testProxy(proxy) {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 3000);
    const resp = await fetch("http://ip-api.com/json/?fields=countryCode,ip,query", {
      signal: ctrl.signal,
      headers: { "User-Agent": "FrenchIPMasker/1.0" }
    });
    const data = await resp.json();
    if (data.countryCode === "FR") {
      return { proxy, ip: data.ip || data.query, latency: Math.round(resp.headers.get("x-response-time") || 0) };
    }
  } catch (e) {}
  return null;
}

async function testBatch(proxies, workers = 8) {
  const results = [];
  const queue = [...proxies];
  const running = new Set();

  async function worker() {
    while (queue.length > 0) {
      const p = queue.shift();
      if (!p) break;
      running.add(p);
      const r = await testProxy(p);
      running.delete(p);
      if (r) {
        results.push(r);
        chrome.storage.local.set({ pool: results });
      }
      const progress = proxies.length - queue.length;
      if (progress % 5 === 0) {
        chrome.storage.local.set({ progress: { done: progress, total: proxies.length, found: results.length }});
      }
    }
  }

  await Promise.all(Array(workers).fill(0).map(() => worker()));
  return results;
}

// ─── Scraping ─────────────────────────────────────────
async function scrapeProxies() {
  const all = new Set();
  for (const url of PROXY_SOURCES) {
    try {
      const ctrl = new AbortController();
      setTimeout(() => ctrl.abort(), 8000);
      const resp = await fetch(url, { signal: ctrl.signal });
      const text = await resp.text();
      for (const line of text.split(/[\r\n]+/)) {
        const p = line.trim();
        if (p.includes(':') && p.length < 25 && !p.startsWith('#')) {
          all.add(p);
        }
      }
    } catch (e) {}
  }
  return [...all];
}

// ─── Main Loop ────────────────────────────────────────
async function startProxyPool() {
  if (running) return;
  running = true;

  // Notify UI
  chrome.storage.local.set({ status: "starting", progress: { done: 0, total: 0, found: 0 } });

  // Phase 1: Try cached proxies first
  const cached = (await chrome.storage.local.get('allProxies')).allProxies || [];
  if (cached.length > 0) {
    chrome.storage.local.set({ status: "testing_cached" });
    pool = await testBatch(cached.slice(0, 30), 12);
  }

  // Phase 2: Scrape web
  if (pool.length < 3) {
    chrome.storage.local.set({ status: "scraping", progress: { done: 0, total: 0, found: 0 } });
    const scraped = await scrapeProxies();
    await chrome.storage.local.set({ allProxies: scraped });
    pool = await testBatch(scraped.slice(0, 40), 10);
  }

  if (pool.length > 0) {
    const best = pool.sort((a, b) => a.latency - b.latency)[0];
    applyProxy(best.proxy);
    active = true;
    chrome.storage.local.set({
      status: "active",
      pool: pool,
      current: best,
      active: true
    });
    // Continue scraping in background
    scheduleRefresh();
  } else {
    chrome.storage.local.set({ status: "noproxy", active: false });
  }
  running = false;
}

function stopProxyPool() {
  removeProxy();
  active = false;
  chrome.storage.local.set({ status: "idle", active: false });
}

function rotateProxy() {
  if (pool.length < 2) return;
  const current = currentProxy;
  const available = pool.filter(p => p.proxy !== current);
  if (available.length === 0) return;
  const best = available.sort((a, b) => a.latency - b.latency)[0];
  applyProxy(best.proxy);
  chrome.storage.local.set({ current: best, pool: pool });
}

async function scheduleRefresh() {
  // Refresh pool every 2 minutes
  chrome.alarms.create('refresh', { periodInMinutes: 2 });
}

// ─── Background refresh ───────────────────────────────
async function backgroundRefresh() {
  if (!active || running) return;
  running = true;
  try {
    const scraped = await scrapeProxies();
    await chrome.storage.local.set({ allProxies: scraped });
    const newPool = await testBatch(scraped.slice(0, 20), 8);
    if (newPool.length > 0) {
      // Merge with existing pool
      const existingProxies = new Set(pool.map(p => p.proxy));
      for (const p of newPool) {
        if (!existingProxies.has(p.proxy)) pool.push(p);
      }
      // Keep max 50
      pool = pool.slice(0, 50);
    }
  } catch (e) {}
  running = false;
}

// ─── Message handlers ─────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "start") {
    startProxyPool().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg.action === "stop") {
    stopProxyPool();
    sendResponse({ ok: true });
    return false;
  }
  if (msg.action === "rotate") {
    rotateProxy();
    const s = pool.length;
    const ip = currentProxy ? currentProxy : null;
    sendResponse({ ok: true, pool: s, ip: ip });
    return false;
  }
  if (msg.action === "status") {
    chrome.storage.local.get(['status','active','current','pool','progress'], (data) => {
      sendResponse(data);
    });
    return true;
  }
});

// ─── Alarms ───────────────────────────────────────────
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'refresh') backgroundRefresh();
});

// ─── Init ─────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ status: "idle", active: false, pool: [], current: null });
});
