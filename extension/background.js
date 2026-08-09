// FrenchIPMasker v5.0 - Background Service Worker
// Pool proxy FR (scraping) + Cloudflare Worker (fallback)
// Uses chrome.proxy API + WebRTC blocking

const PROXY_SOURCES = [
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=FR&ssl=all&anonymity=all",
  "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
  "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
  "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
  "https://www.proxy-list.download/api/v1/get?type=http",
];

let pool = [];
let current = null;
let active = false;
let running = false;
let cfWorker = "";

// ─── Storage helpers ─────────────────────────────────
async function get(k) { return (await chrome.storage.local.get(k))[k]; }
async function set(obj) { return chrome.storage.local.set(obj); }

// ─── Cloudflare Worker ───────────────────────────────
async function checkWorkerIP(workerUrl) {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 5000);
    const resp = await fetch(`${workerUrl}/ip`, { signal: ctrl.signal });
    return await resp.json();
  } catch (e) {
    return null;
  }
}

// ─── Proxy testing ───────────────────────────────────
async function testOne(proxy) {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 3000);
    const resp = await fetch("http://ip-api.com/json/?fields=countryCode,ip,query", {
      signal: ctrl.signal
    });
    const data = await resp.json();
    if (data.countryCode === "FR") {
      return { proxy, ip: data.ip || data.query };
    }
  } catch (e) {}
  return null;
}

async function testBatch(list, workers = 12) {
  const results = [];
  const queue = [...list];
  const seen = new Set(pool.map(p => p.proxy));
  const todo = queue.filter(p => !seen.has(p));

  async function worker() {
    while (todo.length > 0) {
      const p = todo.shift();
      if (!p) break;
      const r = await testOne(p);
      if (r) {
        results.push(r);
        await set({ pool: [...pool, ...results].slice(0, 50) });
      }
      const progress = list.length - todo.length;
      if (progress % 5 === 0) {
        await set({ progress: { done: progress, total: list.length, found: results.length }});
      }
    }
  }

  await Promise.all(Array(workers).fill(0).map(() => worker()));
  return results;
}

// ─── Scraping ─────────────────────────────────────────
async function scrape() {
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

// ─── Apply proxy ──────────────────────────────────────
function applyProxy(proxyStr, cfUrl = null) {
  if (cfUrl && (!proxyStr || pool.length === 0)) {
    // Cloudflare Worker fallback - PAC script
    const config = {
      mode: "pac_script",
      pacScript: {
        data: `function FindProxyForURL(url, host) { return "PROXY ${cfUrl.replace(/https?:\/\//,'')}:80"; }`
      }
    };
    chrome.proxy.settings.set({ value: config, scope: 'regular' });
    current = { proxy: cfUrl, ip: "CF Paris", cf: true };
  } else if (proxyStr) {
    const [host, port] = proxyStr.split(':');
    chrome.proxy.settings.set({
      value: {
        mode: "fixed_servers",
        rules: { singleProxy: { scheme: "http", host, port: parseInt(port) } }
      },
      scope: 'regular'
    });
    current = { proxy: proxyStr, ip: proxyStr, cf: false };
  }
}

function removeProxy() {
  chrome.proxy.settings.clear({ scope: 'regular' });
  current = null;
}

// ─── Main flow ────────────────────────────────────────
async function start() {
  if (running) return;
  running = true;
  cfWorker = await get('cfWorker') || "";

  await set({ status: "starting", progress: { done: 0, total: 0, found: 0 } });

  // Phase 1: Check CF Worker first
  if (cfWorker) {
    const info = await checkWorkerIP(cfWorker);
    if (info) {
      await set({ cfInfo: info });
    }
  }

  // Phase 2: Try cached proxies
  const cached = await get('allProxies') || [];
  if (cached.length > 0) {
    await set({ status: "testing_cached" });
    const newPool = await testBatch(cached.slice(0, 30), 12);
    if (newPool.length > 0) {
      pool = newPool;
      applyProxy(newPool[0].proxy);
      active = true;
      await set({ status: "active", pool, current: newPool[0], active: true });
      running = false;
      scheduleRefresh();
      return;
    }
  }

  // Phase 3: Scrape + test
  await set({ status: "scraping" });
  const scraped = await scrape();
  await set({ allProxies: scraped, progress: { done: 0, total: scraped.length, found: 0 } });
  pool = await testBatch(scraped.slice(0, 40), 12);

  if (pool.length > 0) {
    applyProxy(pool[0].proxy);
    active = true;
    await set({ status: "active", pool, current: pool[0], active: true });
    scheduleRefresh();
  } else if (cfWorker) {
    // Fallback: use CF Worker as proxy
    applyProxy(null, cfWorker);
    active = true;
    await set({ status: "active", pool: [], current: { proxy: cfWorker, ip: "CF Paris", cf: true }, active: true, cfFallback: true });
  } else {
    await set({ status: "noproxy", active: false });
  }
  running = false;
}

function stop() {
  removeProxy();
  active = false;
  set({ status: "idle", active: false });
}

function rotate() {
  if (pool.length > 1) {
    const cur = current?.proxy;
    const avail = pool.filter(p => p.proxy !== cur);
    if (avail.length > 0) {
      const best = avail.sort(() => Math.random() - 0.5)[0];
      applyProxy(best.proxy);
      set({ current: best, pool });
      return best;
    }
  }
  // If pool exhausted, try CF
  if (cfWorker && (!current || !current.cf)) {
    applyProxy(null, cfWorker);
    set({ current: { proxy: cfWorker, ip: "CF Paris", cf: true } });
    return { proxy: cfWorker, ip: "CF Paris", cf: true };
  }
  return current;
}

// ─── Background refresh ───────────────────────────────
async function bgRefresh() {
  if (!active || running) return;
  running = true;
  try {
    const scraped = await scrape();
    await set({ allProxies: scraped });
    const fresh = await testBatch(scraped.slice(0, 20), 8);
    if (fresh.length > 0) {
      const existing = new Set(pool.map(p => p.proxy));
      for (const p of fresh) {
        if (!existing.has(p.proxy)) pool.push(p);
      }
      pool = pool.slice(0, 50);
      await set({ pool });
    }
  } catch (e) {}
  running = false;
}

function scheduleRefresh() {
  chrome.alarms.create('refresh', { periodInMinutes: 3 });
}

// ─── WebRTC blocking ──────────────────────────────────
async function blockWebRTC() {
  // Use declarativeNetRequest to block STUN/TURN
  const rules = [{
    id: 1,
    priority: 1,
    action: { type: "block" },
    condition: {
      urlFilter: "*stun*",
      resourceTypes: ["xmlhttprequest", "websocket"]
    }
  }, {
    id: 2,
    priority: 1,
    action: { type: "block" },
    condition: {
      urlFilter: "*turn*",
      resourceTypes: ["xmlhttprequest", "websocket"]
    }
  }];
  try {
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: rules.map(r => r.id),
      addRules: rules
    });
  } catch (e) {}
}

// ─── Messages ─────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "start") {
    start().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg.action === "stop") {
    stop();
    sendResponse({ ok: true });
  }
  if (msg.action === "rotate") {
    const r = rotate();
    sendResponse({ ok: true, ip: r?.ip, pool: pool.length });
  }
  if (msg.action === "status") {
    chrome.storage.local.get(['status','active','current','pool','progress','cfInfo','cfFallback','cfWorker'], (d) => {
      sendResponse(d);
    });
    return true;
  }
  if (msg.action === "setWorker") {
    cfWorker = msg.url || "";
    set({ cfWorker });
    sendResponse({ ok: true });
  }
});

// ─── Alarms ───────────────────────────────────────────
chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === 'refresh') bgRefresh();
});

// ─── Init ─────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(async () => {
  await set({ status: "idle", active: false, pool: [], current: null, cfWorker: "" });
  await blockWebRTC();
});

// Restore state on startup
(async () => {
  const wasActive = await get('active');
  if (wasActive) {
    const saved = await get('cfWorker');
    if (saved) cfWorker = saved;
    await start();
  }
  await blockWebRTC();
})();
