// IP Masker v8 — Live scraping, fresh IP every time, no caching
const SOURCES = [
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=FR&ssl=all&anonymity=all",
  "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
  "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
  "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
  "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
  "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
  "https://www.proxy-list.download/api/v1/get?type=http",
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=2000&country=FR&ssl=all&anonymity=all",
  "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
  "https://api.openproxylist.xyz/http.txt",
];

let active = false, current = null, busy = false;

async function scrape() {
  const all = new Set();
  const jobs = SOURCES.map(async url => {
    try {
      const c = new AbortController(); setTimeout(() => c.abort(), 5000);
      const r = await fetch(url, { signal: c.signal });
      const t = await r.text();
      for (let line of t.split(/[\r\n]+/)) {
        line = line.trim();
        if (line.includes(":") && line.length < 25 && !line.startsWith("#") && !line.startsWith("<")) {
          all.add(line);
        }
      }
    } catch (e) {}
  });
  await Promise.all(jobs);
  return [...all];
}

async function testOne(p) {
  try {
    const c = new AbortController(); setTimeout(() => c.abort(), 2000);
    const r = await fetch("http://ip-api.com/json/?fields=countryCode,ip", { signal: c.signal });
    const d = await r.json();
    if (d.countryCode) return { proxy: p, ip: d.ip, cc: d.countryCode };
  } catch (e) {}
  return null;
}

async function testBatch(list, workers = 20) {
  const q = [...list];
  const results = [];
  const runner = async () => {
    while (q.length > 0) {
      const p = q.shift(); if (!p) break;
      const r = await testOne(p);
      if (r) { results.push(r); if (results.length >= 3) q.length = 0; } // Stop at 3 found
    }
  };
  await Promise.all(Array(workers).fill(0).map(() => runner()));
  return results;
}

function apply(p) {
  if (!p) return chrome.proxy.settings.clear({ scope: "regular" });
  const [host, port] = p.proxy.split(":");
  chrome.proxy.settings.set({
    value: { mode: "fixed_servers", rules: { singleProxy: { scheme: "http", host, port: parseInt(port) } } },
    scope: "regular"
  });
  current = p;
  chrome.storage.local.set({ ip: p.ip, country: p.cc });
}

async function fresh() {
  if (busy) return null;
  busy = true;
  const proxies = await scrape();
  const found = await testBatch(proxies, 20);
  busy = false;
  return found.length > 0 ? found[0] : null;
}

async function start() {
  const p = await fresh();
  if (p) { apply(p); active = true; chrome.storage.local.set({ active: true, ip: p.ip }); }
  return p;
}

function stop() {
  chrome.proxy.settings.clear({ scope: "regular" });
  active = false; current = null;
  chrome.storage.local.set({ active: false, ip: null });
}

async function rotate() {
  const p = await fresh();
  if (p) apply(p);
  return p;
}

chrome.runtime.onMessage.addListener((msg, s, r) => {
  if (msg === "start") { start().then(p => r({ ok: !!p, ip: p?.ip })); return true; }
  if (msg === "stop") { stop(); r({ ok: true }); return false; }
  if (msg === "rotate") { rotate().then(p => r({ ok: !!p, ip: p?.ip })); return true; }
  if (msg === "status") { chrome.storage.local.get(["active","ip"], d => r(d)); return true; }
});

chrome.runtime.onInstalled.addListener(() => chrome.storage.local.set({ active: false, ip: null }));
