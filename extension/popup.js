// FrenchIPMasker v6 — Popup (no setup, 1-click)
const $ = id => document.getElementById(id);
const bg = chrome.runtime;
let active = false;

const sEl = $("status"), iEl = $("ip"), lEl = $("loc");
const pEl = $("pool"), rEl = $("prog");
const tBtn = $("toggleBtn"), rotBtn = $("rotBtn");
const info = $("info");

// ─── Toggle ───────────────────────────────────────────
tBtn.addEventListener("click", async () => {
  if (active) {
    tBtn.disabled = true; tBtn.textContent = "Arrêt...";
    await new Promise(r => bg.sendMessage({ action: "stop" }, r));
    setUI("idle");
  } else {
    tBtn.disabled = true; tBtn.textContent = "Recherche de proxys FR...";
    rEl.textContent = "Test de 80+ proxys pré-chargés...";
    await new Promise(r => bg.sendMessage({ action: "start" }, r));
    poll();
  }
});

// ─── Rotate ──────────────────────────────────────────
rotBtn.addEventListener("click", async () => {
  rotBtn.disabled = true; rotBtn.textContent = "...";
  const r = await new Promise(r2 => bg.sendMessage({ action: "rotate" }, r2));
  if (r && r.ip) {
    iEl.textContent = r.ip;
    pEl.textContent = `Pool : ${r.total} proxys FR | rotation ∞`;
    rotBtn.textContent = "🔄 Changer d'IP (instantané)";
  }
  rotBtn.disabled = false;
});

// ─── Poll status ──────────────────────────────────────
async function poll() {
  const d = await new Promise(r => bg.sendMessage({ action: "status" }, r));
  if (!d) return;
  if (d.active) { setUI("active", d); return; }
  if (d.status === "starting" || d.status === "testing" || d.status === "scraping") {
    setUI("loading", d);
    setTimeout(poll, 1200);
    return;
  }
  if (d.status === "noproxy") { setUI("noproxy"); return; }
  setUI("idle");
}

function setUI(state, data = {}) {
  switch (state) {
    case "idle":
      active = false;
      sEl.textContent = "○ Inactif"; sEl.className = "status s-off";
      iEl.textContent = "—"; iEl.className = "ip";
      lEl.textContent = "Extension prête";
      pEl.textContent = ""; rEl.textContent = "";
      tBtn.textContent = "Activer le masquage";
      tBtn.className = "btn btn-start"; tBtn.disabled = false;
      rotBtn.classList.add("hidden"); info.classList.remove("hidden");
      break;

    case "active":
      active = true;
      sEl.textContent = "● Actif"; sEl.className = "status s-on";
      const c = data.current || {};
      iEl.textContent = c.ip || "..."; iEl.className = "ip ip-on";
      lEl.textContent = "France 🇫🇷";
      const n = (data.pool || []).length;
      pEl.textContent = `Pool : ${n} proxys FR | rotation ∞`;
      rEl.textContent = "";
      tBtn.textContent = "Désactiver";
      tBtn.className = "btn btn-stop"; tBtn.disabled = false;
      rotBtn.classList.remove("hidden"); rotBtn.disabled = false;
      info.classList.add("hidden");
      break;

    case "loading":
      const p = data.progress || {};
      sEl.textContent = "⟳ Test..."; sEl.className = "status s-off";
      iEl.textContent = "..."; iEl.className = "ip";
      if (p.total) {
        rEl.textContent = `${p.done}/${p.total} testés · ${p.found||0} FR trouvés`;
      } else {
        rEl.textContent = "Scraping des proxys FR...";
      }
      tBtn.textContent = "Recherche..."; tBtn.disabled = true;
      rotBtn.classList.add("hidden");
      break;

    case "noproxy":
      active = false;
      sEl.textContent = "✕ Échec"; sEl.className = "status s-err";
      iEl.textContent = "Aucun proxy FR"; iEl.className = "ip";
      lEl.textContent = "Vérifiez votre connexion";
      pEl.textContent = ""; rEl.textContent = "";
      tBtn.textContent = "Réessayer";
      tBtn.className = "btn btn-start"; tBtn.disabled = false;
      rotBtn.classList.add("hidden");
      break;
  }
}

// ─── Init ─────────────────────────────────────────────
poll();
setInterval(() => { if (active) poll(); }, 6000);
