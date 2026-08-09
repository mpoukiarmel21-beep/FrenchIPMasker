// Ultra-minimal IP masker — one button, zero config, just works
const POOL = [
  "51.158.110.234:3128","51.158.108.215:3128","51.159.30.49:3128","51.158.111.229:3128",
  "51.158.98.123:3128","163.172.176.38:3128","51.158.154.47:3128","51.158.107.202:3128",
  "51.159.6.60:3128","51.158.123.35:3128","163.172.212.35:3128","193.70.114.126:3128",
  "51.158.68.131:3128","51.158.68.24:3128","51.158.100.191:3128","54.38.80.108:3128",
  "51.75.144.249:3128","51.77.149.179:3128","188.165.194.79:3128","193.70.114.125:3128",
  "51.158.119.88:3128","51.159.195.47:3128","51.158.79.48:3128","51.159.196.45:3128",
  "51.158.202.17:3128","51.158.119.212:3128","163.172.132.38:3128","51.158.103.129:3128",
  "51.158.113.130:3128","51.159.14.110:3128","51.158.147.235:3128","51.159.31.42:3128",
  "51.158.120.89:3128","51.159.8.210:3128","51.158.93.45:3128","51.158.66.75:3128",
  "51.158.78.19:3128","51.158.109.44:3128","51.158.204.64:3128","51.158.153.184:3128",
  "51.158.90.240:3128","163.172.142.124:3128","51.158.199.205:3128","51.159.24.172:3128",
  "51.158.74.143:3128","51.159.60.71:3128","51.159.8.201:3128","51.158.123.4:3128",
  "163.172.149.124:3128","51.158.70.109:3128","51.158.98.212:3128","51.158.111.54:3128",
  "51.158.126.170:3128","51.158.105.169:3128","54.38.80.102:3128","51.158.155.24:3128",
  "51.158.113.178:3128","51.159.57.159:3128","51.158.108.133:3128","51.158.82.91:3128",
  "51.159.11.222:3128","51.159.61.214:3128","51.158.97.130:3128","51.158.79.139:3128",
  "51.158.69.31:3128","51.158.120.245:3128","51.158.118.112:3128","51.158.94.187:3128",
  "51.158.112.209:3128","51.158.151.15:3128","51.158.70.243:3128","51.158.78.127:3128",
  "51.159.4.26:3128","51.158.67.85:3128","51.158.125.54:3128","51.158.77.123:3128",
  "51.159.52.40:3128","51.158.119.202:3128"
];

let working = [];
let current = null;
let active = false;

async function test(p) {
  try {
    const c = new AbortController();
    setTimeout(() => c.abort(), 2000);
    const r = await fetch("http://ip-api.com/json/?fields=countryCode,ip", { signal: c.signal });
    const d = await r.json();
    if (d.countryCode) return { proxy: p, ip: d.ip, country: d.countryCode };
  } catch (e) {}
  return null;
}

async function findProxy() {
  const n = 20;
  const batch = POOL.sort(() => Math.random() - 0.5).slice(0, n);
  const results = [];
  const queue = [...batch];

  const worker = async () => {
    while (queue.length > 0) {
      const p = queue.shift();
      if (!p) break;
      const r = await test(p);
      if (r) results.push(r);
    }
  };
  await Promise.all(Array(8).fill(0).map(() => worker()));
  working = results;
  return results.length > 0 ? results[0] : null;
}

function apply(p) {
  if (!p) { chrome.proxy.settings.clear({ scope: "regular" }); current = null; return; }
  const [host, port] = p.proxy.split(":");
  chrome.proxy.settings.set({
    value: { mode: "fixed_servers", rules: { singleProxy: { scheme: "http", host, port: parseInt(port) } } },
    scope: "regular"
  });
  current = p;
  chrome.storage.local.set({ ip: p.ip });
}

async function start() {
  const p = await findProxy();
  if (p) {
    apply(p);
    active = true;
    chrome.storage.local.set({ active: true, ip: p.ip });
    chrome.alarms.create("refresh", { periodInMinutes: 5 });
  }
  return p;
}

function stop() {
  chrome.proxy.settings.clear({ scope: "regular" });
  active = false; current = null;
  chrome.storage.local.set({ active: false, ip: null });
  chrome.alarms.clear("refresh");
}

async function rotate() {
  if (!active) return;
  const avail = working.filter(w => w.proxy !== (current?.proxy || ""));
  if (avail.length > 0) {
    apply(avail[Math.floor(Math.random() * avail.length)]);
  } else {
    const p = await findProxy();
    if (p) apply(p);
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg === "start") { start().then(p => sendResponse({ ok: !!p, ip: p?.ip })); return true; }
  if (msg === "stop") { stop(); sendResponse({ ok: true }); }
  if (msg === "rotate") {
    rotate().then(() => sendResponse({ ok: true, ip: current?.ip }));
    return true;
  }
  if (msg === "status") {
    chrome.storage.local.get(["active","ip"], d => sendResponse(d));
    return true;
  }
});

chrome.alarms.onAlarm.addListener(a => { if (a.name === "refresh") rotate(); });

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ active: false, ip: null });
});
