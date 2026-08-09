// FrenchIPMasker v5.0 - Popup Controller
const $ = id => document.getElementById(id);
const bg = chrome.runtime;
let active = false;

const statusEl = $("status"), ipEl = $("ip"), locEl = $("loc");
const poolEl = $("pool"), progEl = $("prog"), cfEl = $("cfBadge");
const toggleBtn = $("toggleBtn"), rotBtn = $("rotBtn");
const infoEl = $("info"), cfgPanel = $("cfgPanel");
const workerInput = $("workerUrl");

// ─── Load saved worker URL ────────────────────────────
chrome.storage.local.get('cfWorker', (d) => {
  if (d.cfWorker) workerInput.value = d.cfWorker;
});

// ─── Save worker URL on change ────────────────────────
workerInput.addEventListener('change', () => {
  const url = workerInput.value.trim();
  chrome.runtime.sendMessage({ action: "setWorker", url });
  chrome.storage.local.set({ cfWorker: url });
});

workerInput.addEventListener('blur', () => {
  workerInput.dispatchEvent(new Event('change'));
});

// ─── Toggle ───────────────────────────────────────────
toggleBtn.addEventListener("click", async () => {
  if (active) {
    toggleBtn.disabled = true;
    toggleBtn.textContent = "Arrêt...";
    await new Promise(r => bg.sendMessage({ action: "stop" }, r));
    setUI("idle");
  } else {
    // Show CF config if no worker URL set
    chrome.storage.local.get('cfWorker', async (d) => {
      if (!d.cfWorker) cfgPanel.classList.remove("hidden");
      toggleBtn.disabled = true;
      toggleBtn.textContent = "Recherche...";
      progEl.textContent = "Scraping + test des proxys...";
      await new Promise(r => bg.sendMessage({ action: "start" }, r));
      checkStatus();
    });
  }
});

// ─── Rotate ──────────────────────────────────────────
rotBtn.addEventListener("click", async () => {
  rotBtn.disabled = true;
  rotBtn.textContent = "...";
  const r = await new Promise(r2 => bg.sendMessage({ action: "rotate" }, r2));
  if (r && r.ip) {
    ipEl.textContent = r.ip;
    poolEl.textContent = r.pool > 0 ? `Pool : ${r.pool} proxys FR` : "via Cloudflare";
    if (r.pool === 0) cfEl.classList.remove("hidden");
  }
  rotBtn.textContent = "🔄 Changer d'IP";
  rotBtn.disabled = false;
});

// ─── Status ──────────────────────────────────────────
async function checkStatus() {
  const d = await new Promise(r => bg.sendMessage({ action: "status" }, r));
  if (!d) return;

  if (d.active && d.status === "active") {
    setUI("active", d);
  } else if (d.status === "starting" || d.status === "scraping" || d.status === "testing_cached") {
    setUI("loading", d);
    setTimeout(checkStatus, 1500);
  } else if (d.status === "noproxy") {
    setUI("noproxy");
  } else {
    setUI("idle");
  }
}

function setUI(state, data = {}) {
  switch (state) {
    case "idle":
      active = false;
      statusEl.textContent = "○ Inactif"; statusEl.className = "status s-off";
      ipEl.textContent = "—"; ipEl.className = "ip";
      locEl.textContent = "Extension prête";
      poolEl.textContent = ""; progEl.textContent = "";
      cfEl.classList.add("hidden");
      toggleBtn.textContent = "Activer le masquage";
      toggleBtn.className = "btn btn-start"; toggleBtn.disabled = false;
      rotBtn.classList.add("hidden"); infoEl.classList.remove("hidden");
      break;

    case "active":
      active = true;
      statusEl.textContent = "● Actif"; statusEl.className = "status s-on";
      const cur = data.current || {};
      ipEl.textContent = cur.ip || "..."; ipEl.className = "ip ip-on";
      locEl.textContent = cur.cf ? "Cloudflare Paris 🇫🇷" : "France 🇫🇷 (proxy)";
      const s = (data.pool || []).length;
      poolEl.textContent = s > 0 ? `Pool : ${s} proxys FR` : "via Cloudflare Paris";
      if (data.cfFallback || cur.cf) cfEl.classList.remove("hidden");
      else cfEl.classList.add("hidden");
      toggleBtn.textContent = "Désactiver";
      toggleBtn.className = "btn btn-stop"; toggleBtn.disabled = false;
      rotBtn.classList.remove("hidden"); rotBtn.disabled = false;
      infoEl.classList.add("hidden"); progEl.textContent = "";
      cfgPanel.classList.add("hidden");
      break;

    case "loading":
      const p = data.progress || {};
      statusEl.textContent = "⟳ Recherche..."; statusEl.className = "status s-off";
      ipEl.textContent = "..."; ipEl.className = "ip";
      progEl.textContent = p.total ? `${p.done}/${p.total} testés · ${p.found||0} FR` : "Scraping...";
      toggleBtn.textContent = "Recherche..."; toggleBtn.disabled = true;
      rotBtn.classList.add("hidden");
      break;

    case "noproxy":
      active = false;
      statusEl.textContent = "✕ Aucune IP FR"; statusEl.className = "status s-err";
      ipEl.textContent = "Échec"; ipEl.className = "ip";
      locEl.textContent = "Ajoute un worker CF ou réessaie";
      poolEl.textContent = ""; progEl.textContent = "";
      toggleBtn.textContent = "Réessayer";
      toggleBtn.className = "btn btn-start"; toggleBtn.disabled = false;
      rotBtn.classList.add("hidden");
      cfgPanel.classList.remove("hidden");
      break;
  }
}

// ─── Init ─────────────────────────────────────────────
checkStatus();
setInterval(() => { if (active) checkStatus(); }, 5000);
