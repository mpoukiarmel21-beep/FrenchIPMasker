"use strict";

/*
 * IP Masker FR — Firefox
 * Scraping live de proxies FR + test en VRAI (chaque test passe par le proxy,
 * l'IP de sortie est vérifiée via ip-api.com) puis routage de tout le trafic
 * par le proxy via browser.proxy.onRequest.
 */

const SOURCES_FR = [
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=FR&ssl=all&anonymity=all"
];
const SOURCES_GLOBAL = [
  "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
  "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
  "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
  "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
  "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt"
];

const BYPASS_HOSTS = new Set(
  SOURCES_FR.concat(SOURCES_GLOBAL)
    .map((u) => { try { return new URL(u).hostname; } catch (e) { return ""; } })
    .filter(Boolean)
);
BYPASS_HOSTS.add("ip-api.com");

let active = false;
let currentProxy = null;
let usedProxies = new Set();
let usedIPs = new Set();
let busy = false;

function proxyInfo(p) {
  const i = p.lastIndexOf(":");
  return { type: "http", host: p.slice(0, i), port: parseInt(p.slice(i + 1), 10) };
}

/* Routage : 1) test (param __fp) → proxy candidat
   2) sources de scraping → direct (pour ne pas casser le scraping)
   3) masquage actif → proxy FR
   4) sinon → direct */
browser.proxy.onRequest.addListener(
  (details) => {
    try {
      const u = new URL(details.url);
      const fp = u.searchParams.get("__fp");
      if (fp) {
        return [proxyInfo(fp), null];
      }
      if (BYPASS_HOSTS.has(u.hostname)) {
        return { type: "direct" };
      }
      if (active && currentProxy) {
        return [proxyInfo(currentProxy), null];
      }
    } catch (e) {}
    return { type: "direct" };
  },
  { urls: ["<all_urls>"] }
);

browser.proxy.onError.addListener((e) => console.error("IP Masker proxy error:", e));

async function getText(url, timeoutMs) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), timeoutMs);
  try {
    const r = await fetch(url, { signal: c.signal, cache: "no-store" });
    return await r.text();
  } finally {
    clearTimeout(t);
  }
}

function addLines(set, text) {
  for (const line of text.split(/[\r\n]+/)) {
    const l = line.trim();
    if (/^\d{1,3}(\.\d{1,3}){3}:\d{2,5}$/.test(l)) set.add(l);
  }
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

async function scrape() {
  const fr = new Set();
  const glob = new Set();
  const jobs = [];
  for (const u of SOURCES_FR) jobs.push(getText(u, 9000).then((t) => addLines(fr, t), () => {}));
  for (const u of SOURCES_GLOBAL) jobs.push(getText(u, 9000).then((t) => addLines(glob, t), () => {}));
  await Promise.allSettled(jobs);
  const ordered = [...shuffle([...fr]), ...shuffle([...glob])];
  return ordered.filter((p) => !usedProxies.has(p)).slice(0, 350);
}

/* Test EN VRAI : le fetch part AVEC le proxy (routé par __fp dans onRequest).
   ip-api renvoie l'IP de SORTIE réelle du proxy + son pays. */
async function test(p) {
  const url = `http://ip-api.com/json/?fields=status,countryCode,query&__fp=${encodeURIComponent(p)}`;
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), 3500);
  try {
    const r = await fetch(url, { signal: c.signal, cache: "no-store" });
    const d = await r.json();
    if (d && d.status === "success" && d.countryCode === "FR" && d.query && d.query !== "0.0.0.0") {
      return { proxy: p, ip: d.query };
    }
  } catch (e) {
  } finally {
    clearTimeout(t);
  }
  return null;
}

async function testBatch(list, workers = 20, need = 3) {
  const q = [...list];
  const found = [];
  const run = async () => {
    while (q.length > 0) {
      if (found.length >= need) return;
      const p = q.shift();
      if (!p) return;
      const r = await test(p);
      if (r && !usedIPs.has(r.ip)) found.push(r);
    }
  };
  await Promise.all(Array(workers).fill(0).map(run));
  return found;
}

async function fresh() {
  if (busy) return null;
  busy = true;
  try {
    const candidates = await scrape();
    const found = await testBatch(candidates, 20, 3);
    if (found.length === 0) return null;
    const best = found[0];
    usedProxies.add(best.proxy);
    usedIPs.add(best.ip);
    return best;
  } finally {
    busy = false;
  }
}

async function start() {
  const r = await fresh();
  if (r) {
    currentProxy = r.proxy;
    active = true;
    await browser.storage.local.set({ active: true, ip: r.ip, proxy: r.proxy });
  }
  return r;
}

async function stop() {
  active = false;
  currentProxy = null;
  await browser.storage.local.set({ active: false, ip: null, proxy: null });
}

async function rotate() {
  const r = await fresh();
  if (r) {
    currentProxy = r.proxy;
    active = true;
    await browser.storage.local.set({ active: true, ip: r.ip, proxy: r.proxy });
  }
  return r;
}

browser.runtime.onMessage.addListener(async (msg) => {
  if (msg === "start") {
    const r = await start();
    return { ok: !!r, ip: r ? r.ip : null };
  }
  if (msg === "stop") {
    await stop();
    return { ok: true };
  }
  if (msg === "rotate") {
    const r = await rotate();
    return { ok: !!r, ip: r ? r.ip : null };
  }
  if (msg === "status") {
    const s = await browser.storage.local.get(["active", "ip"]);
    return { active: !!s.active, ip: s.ip || null };
  }
});

browser.runtime.onInstalled.addListener(async () => {
  const s = await browser.storage.local.get(["active", "ip", "proxy"]);
  active = !!s.active;
  if (active && s.proxy) {
    currentProxy = s.proxy;
  }
});
