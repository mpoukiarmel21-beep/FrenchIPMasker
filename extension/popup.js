// FrenchIPMasker - Popup Controller
const $ = id => document.getElementById(id);
const bg = chrome.runtime;

let active = false;

// ─── UI Elements ──────────────────────────────────────
const statusEl = $("status");
const ipEl = $("ip");
const locEl = $("loc");
const poolEl = $("pool");
const progEl = $("prog");
const toggleBtn = $("toggleBtn");
const rotBtn = $("rotBtn");
const infoEl = $("info");

// ─── Toggle ───────────────────────────────────────────
toggleBtn.addEventListener("click", async () => {
  if (active) {
    toggleBtn.disabled = true;
    toggleBtn.textContent = "Arrêt...";
    await new Promise(r => bg.sendMessage({ action: "stop" }, r));
    setUI("idle");
  } else {
    toggleBtn.disabled = true;
    toggleBtn.textContent = "Recherche de proxys FR...";
    progEl.textContent = "Scraping...";
    poolEl.textContent = "";
    await new Promise(r => bg.sendMessage({ action: "start" }, r));
    checkStatus();
  }
});

// ─── Rotate ──────────────────────────────────────────
rotBtn.addEventListener("click", async () => {
  rotBtn.disabled = true;
  rotBtn.textContent = "Rotation...";
  const resp = await new Promise(r => bg.sendMessage({ action: "rotate" }, r));
  if (resp && resp.ip) {
    ipEl.textContent = resp.ip;
    poolEl.textContent = `Pool : ${resp.pool} proxys FR | ${resp.pool > 10 ? '∞' : resp.pool} rotations`;
  }
  rotBtn.textContent = "🔄 Changer d'IP française";
  rotBtn.disabled = false;
});

// ─── Status check ─────────────────────────────────────
async function checkStatus() {
  const data = await new Promise(r => bg.sendMessage({ action: "status" }, r));
  if (!data) return;

  if (data.active && data.status === "active") {
    setUI("active", data);
  } else if (data.status === "starting" || data.status === "scraping" || data.status === "testing_cached") {
    setUI("loading", data);
    setTimeout(checkStatus, 1500);
  } else if (data.status === "noproxy") {
    setUI("noproxy");
  } else {
    setUI("idle");
  }
}

function setUI(state, data = {}) {
  switch (state) {
    case "idle":
      active = false;
      statusEl.textContent = "○ Inactif"; statusEl.className = "status off";
      ipEl.textContent = "—"; ipEl.className = "ip";
      locEl.textContent = "Extension prête";
      poolEl.textContent = "";
      progEl.textContent = "";
      toggleBtn.textContent = "Activer le masquage";
      toggleBtn.className = "btn btn-start";
      toggleBtn.disabled = false;
      rotBtn.classList.add("hidden");
      infoEl.classList.remove("hidden");
      break;

    case "active":
      active = true;
      statusEl.textContent = "● Actif"; statusEl.className = "status on";
      const ip = data.current ? data.current.ip : "...";
      ipEl.textContent = ip; ipEl.className = "ip active";
      locEl.textContent = "France 🇫🇷";
      const s = (data.pool || []).length;
      poolEl.textContent = `Pool : ${s} proxys FR`;
      toggleBtn.textContent = "Désactiver";
      toggleBtn.className = "btn btn-stop";
      toggleBtn.disabled = false;
      rotBtn.classList.remove("hidden");
      rotBtn.disabled = false;
      infoEl.classList.add("hidden");
      progEl.textContent = "";
      break;

    case "loading":
      const p = data.progress || {};
      statusEl.textContent = "⟳ Recherche..."; statusEl.className = "status off";
      ipEl.textContent = "..."; ipEl.className = "ip";
      if (p.total) {
        progEl.textContent = `${p.done}/${p.total} testés · ${p.found || 0} FR trouvés`;
      } else {
        progEl.textContent = data.status === "scraping" ? "Scraping du web..." : "Test des proxys...";
      }
      toggleBtn.textContent = "Recherche...";
      toggleBtn.disabled = true;
      rotBtn.classList.add("hidden");
      break;

    case "noproxy":
      active = false;
      statusEl.textContent = "✕ Aucun proxy FR"; statusEl.className = "status err";
      ipEl.textContent = "Échec"; ipEl.className = "ip";
      locEl.textContent = "Vérifiez votre connexion";
      poolEl.textContent = "";
      toggleBtn.textContent = "Réessayer";
      toggleBtn.className = "btn btn-start";
      toggleBtn.disabled = false;
      rotBtn.classList.add("hidden");
      break;
  }
}

// ─── Init ─────────────────────────────────────────────
checkStatus();

// Auto-refresh status every 5 seconds when active
setInterval(() => { if (active) checkStatus(); }, 5000);
