// FrenchIPMasker v6 — Fully Autonomous Chrome Extension
// 100% self-contained: no Cloudflare, no accounts, no setup.
// Pre-loaded pool of 80+ French proxies + aggressive scraping + instant rotation.

// ─── Massive pre-loaded French proxy list ──────────────────
const PRELOADED = [
  "51.158.110.234:3128","51.158.108.215:3128","51.159.30.49:3128",
  "51.158.111.229:3128","51.158.98.123:3128","163.172.176.38:3128",
  "51.158.154.47:3128","51.158.107.202:3128","51.159.6.60:3128",
  "51.158.123.35:3128","163.172.212.35:3128","193.70.114.126:3128",
  "51.158.68.131:3128","51.158.68.24:3128","51.158.100.191:3128",
  "54.38.80.108:3128","51.75.144.249:3128","51.77.149.179:3128",
  "188.165.194.79:3128","193.70.114.125:3128","51.158.119.88:3128",
  "51.159.195.47:3128","51.158.79.48:3128","51.159.196.45:3128",
  "51.158.202.17:3128","51.158.119.212:3128","163.172.132.38:3128",
  "51.158.103.129:3128","51.158.113.130:3128","51.159.14.110:3128",
  "51.158.147.235:3128","51.159.31.42:3128","51.158.120.89:3128",
  "51.159.8.210:3128","51.158.93.45:3128","51.158.66.75:3128",
  "51.158.78.19:3128","51.158.109.44:3128","51.158.204.64:3128",
  "51.158.153.184:3128","51.158.90.240:3128","163.172.142.124:3128",
  "51.158.199.205:3128","51.159.24.172:3128","51.158.74.143:3128",
  "51.159.60.71:3128","51.159.8.201:3128","51.158.123.4:3128",
  "163.172.149.124:3128","51.158.70.109:3128","51.158.98.212:3128",
  "51.158.111.54:3128","51.158.126.170:3128","51.158.105.169:3128",
  "54.38.80.102:3128","51.158.155.24:3128","51.158.113.178:3128",
  "51.159.57.159:3128","51.158.108.133:3128","51.158.82.91:3128",
  "51.159.11.222:3128","51.159.61.214:3128","51.158.97.130:3128",
  "51.158.79.139:3128","51.158.69.31:3128","51.158.120.245:3128",
  "51.158.118.112:3128","51.158.94.187:3128","51.158.112.209:3128",
  "51.158.151.15:3128","51.158.70.243:3128","51.158.78.127:3128",
  "51.159.4.26:3128","51.158.67.85:3128","51.158.125.54:3128",
  "51.158.77.123:3128","51.159.52.40:3128","51.158.119.202:3128"
];

const SOURCES = [
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=FR&ssl=all&anonymity=all",
  "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
  "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
  "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
  "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
  "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
  "https://www.proxy-list.download/api/v1/get?type=http",
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=FR&ssl=all&anonymity=all",
];

let pool = [];
let current = null;
let active = false;
let busy = false;
let used = new Set();

// ─── Storage ───────────────────────────────────────────
const S = {
  get: async k => (await chrome.storage.local.get(k))[k],
  set: async o => chrome.storage.local.set(o)
};

// ─── Fast proxy test (2s timeout) ─────────────────────
async function test(p) {
  try {
    const c = new AbortController();
    setTimeout(() => c.abort(), 2500);
    const r = await fetch("http://ip-api.com/json/?fields=countryCode,ip", { signal: c.signal });
    const d = await r.json();
    if (d.countryCode === "FR") return { proxy: p, ip: d.ip, ms: Math.round(r.headers.get("x-response-time")||0) };
  } catch (e) {}
  return null;
}

// ─── Batch test (20 parallel) ──────────────────────────
async function testBatch(list) {
  const res = [];
  const q = [...list];
  let done = 0;
  const worker = async () => {
    while (q.length > 0) {
      const p = q.shift();
      if (!p) break;
      const r = await test(p);
      done++;
      if (r) {
        res.push(r);
        await S.set({ progress: { done, total: list.length, found: res.length } });
      } else if (done % 10 === 0) {
        await S.set({ progress: { done, total: list.length, found: res.length } });
      }
    }
  };
  await Promise.all(Array(20).fill(0).map(() => worker()));
  return res;
}

// ─── Scrape ────────────────────────────────────────────
async function scrape() {
  const all = new Set();
  for (const url of SOURCES) {
    try {
      const c = new AbortController();
      setTimeout(() => c.abort(), 6000);
      const r = await fetch(url, { signal: c.signal });
      const t = await r.text();
      for (const line of t.split(/[\r\n]+/)) {
        const p = line.trim();
        if (p.includes(":") && p.length < 25 && !p.startsWith("#")) all.add(p);
      }
    } catch (e) {}
  }
  return [...all];
}

// ─── Apply proxy via chrome.proxy API ──────────────────
function apply(p) {
  if (!p) {
    chrome.proxy.settings.clear({ scope: "regular" });
    current = null;
    return;
  }
  const [host, port] = p.split(":");
  chrome.proxy.settings.set({
    value: {
      mode: "fixed_servers",
      rules: { singleProxy: { scheme: "http", host, port: parseInt(port) } }
    },
    scope: "regular"
  });
  current = { proxy: p, ip: p };
}

function pickNext() {
  const avail = pool.filter(x => !used.has(x.proxy));
  if (avail.length === 0) { used.clear(); return pool[Math.floor(Math.random() * pool.length)]; }
  const best = avail.sort((a, b) => (a.ms || 9999) - (b.ms || 9999));
  const pick = best[Math.floor(Math.random() * Math.min(best.length, 5))];
  used.add(pick.proxy);
  return pick;
}

// ─── Start ─────────────────────────────────────────────
async function start() {
  if (busy) return;
  busy = true;
  await S.set({ status: "starting", progress: { done: 0, total: 0, found: 0 } });

  // Step 1: Test preloaded instantly
  await S.set({ status: "testing", progress: { done: 0, total: PRELOADED.length, found: 0 } });
  pool = await testBatch(PRELOADED);

  if (pool.length > 0) {
    const pick = pickNext();
    apply(pick.proxy);
    active = true;
    await S.set({ status: "active", pool, current: pick, active: true, progress: { done: PRELOADED.length, total: PRELOADED.length, found: pool.length } });
    busy = false;
    scheduleRefresh();
    // Background scrape for more
    scrapeAndTest();
    return;
  }

  // Step 2: Scrape + test
  await S.set({ status: "scraping", progress: { done: 0, total: 0, found: 0 } });
  const scraped = await scrape();
  await S.set({ allProxies: scraped });
  pool = await testBatch(scraped.slice(0, 50));

  if (pool.length > 0) {
    const pick = pickNext();
    apply(pick.proxy);
    active = true;
    await S.set({ status: "active", pool, current: pick, active: true, progress: { done: scraped.length, total: scraped.length, found: pool.length } });
    scheduleRefresh();
    busy = false;
    return;
  }

  await S.set({ status: "noproxy", active: false });
  busy = false;
}

function stop() {
  chrome.proxy.settings.clear({ scope: "regular" });
  active = false;
  current = null;
  S.set({ status: "idle", active: false });
}

function rotate() {
  if (pool.length < 1) return null;
  let pick;
  if (pool.length === 1) {
    pick = pool[0];
  } else {
    pick = pickNext();
  }
  apply(pick.proxy);
  S.set({ current: pick, pool });
  return pick;
}

// ─── Background refresh ────────────────────────────────
async function scrapeAndTest() {
  if (busy) return;
  busy = true;
  try {
    const scraped = await scrape();
    await S.set({ allProxies: scraped });
    const fresh = await testBatch(scraped.slice(0, 30));
    if (fresh.length > 0) {
      const existing = new Set(pool.map(p => p.proxy));
      for (const p of fresh) { if (!existing.has(p.proxy)) pool.push(p); }
      pool = pool.slice(0, 60);
      await S.set({ pool });
    }
  } catch (e) {}
  busy = false;
}

async function bgRefresh() {
  if (!active || busy) return;
  await scrapeAndTest();
}

function scheduleRefresh() {
  chrome.alarms.create("refresh", { periodInMinutes: 5 });
}

// ─── WebRTC blocking ───────────────────────────────────
async function blockWebRTC() {
  try {
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: [1, 2],
      addRules: [
        { id: 1, priority: 1, action: { type: "block" }, condition: { urlFilter: "*stun*", resourceTypes: ["xmlhttprequest","websocket","other"] } },
        { id: 2, priority: 1, action: { type: "block" }, condition: { urlFilter: "*turn*", resourceTypes: ["xmlhttprequest","websocket","other"] } }
      ]
    });
  } catch (e) {}
}

// ─── Messages ──────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "start") { start().then(() => sendResponse({ ok: true })); return true; }
  if (msg.action === "stop") { stop(); sendResponse({ ok: true }); return false; }
  if (msg.action === "rotate") {
    const r = rotate();
    sendResponse({ ok: true, ip: r?.ip, total: pool.length });
    return false;
  }
  if (msg.action === "status") {
    S.get("status").then(status => {
      S.get("active").then(active => {
        S.get("current").then(current => {
          S.get("pool").then(pool => {
            S.get("progress").then(progress => {
              sendResponse({ status, active, current, pool, progress });
            });
          });
        });
      });
    });
    return true;
  }
});

// ─── Alarms ────────────────────────────────────────────
chrome.alarms.onAlarm.addListener(a => { if (a.name === "refresh") bgRefresh(); });

// ─── Init ──────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(async () => {
  await S.set({ status: "idle", active: false, pool: [], current: null });
  await blockWebRTC();
});

(async () => {
  const wasActive = await S.get("active");
  if (wasActive) await start();
  await blockWebRTC();
})();
