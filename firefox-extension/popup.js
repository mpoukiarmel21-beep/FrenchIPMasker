"use strict";

const $ = (id) => document.getElementById(id);

const card = $("card"), dot = $("dot"), statusEl = $("status");
const ipEl = $("ip"), locEl = $("loc");
const toggle = $("toggle"), rotate = $("rotate");
const footer = $("footer");
let active = false;

function setActive(ip) {
  active = true;
  card.className = "card active";
  dot.className = "status-dot on";
  statusEl.textContent = "Protégé";
  statusEl.className = "status-text on";
  ipEl.textContent = ip || "Protégé";
  ipEl.className = "ip-display on";
  locEl.textContent = "IP masquée · France · testée en direct";
  toggle.textContent = "Désactiver";
  toggle.className = "btn btn-danger";
  toggle.disabled = false;
  rotate.classList.remove("hidden");
  rotate.disabled = false;
  footer.classList.add("hidden");
}

function setInactive() {
  active = false;
  card.className = "card inactive";
  dot.className = "status-dot off";
  statusEl.textContent = "Inactif";
  statusEl.className = "status-text off";
  ipEl.textContent = "—";
  ipEl.className = "ip-display off";
  locEl.textContent = "Prêt";
  toggle.textContent = "Activer le masquage";
  toggle.className = "btn btn-primary";
  toggle.disabled = false;
  rotate.classList.add("hidden");
  footer.classList.remove("hidden");
}

function setLoading(msg) {
  toggle.disabled = true;
  toggle.innerHTML = `<span class="spinner"></span> ${msg}`;
}

toggle.addEventListener("click", async () => {
  if (active) {
    setLoading("Arrêt...");
    await browser.runtime.sendMessage("stop");
    setInactive();
  } else {
    setLoading("Test de proxies FR en direct...");
    let r = null;
    try {
      r = await browser.runtime.sendMessage("start");
    } catch (e) {
      r = null;
    }
    if (r && r.ok) {
      setActive(r.ip);
    } else {
      ipEl.textContent = "Échec";
      ipEl.className = "ip-display off";
      locEl.textContent = "Aucun proxy FR vivant · Réessayez";
      toggle.textContent = "Réessayer";
      toggle.className = "btn btn-primary";
      toggle.disabled = false;
    }
  }
});

rotate.addEventListener("click", async () => {
  rotate.disabled = true;
  rotate.innerHTML = `<span class="spinner"></span> IP fraîche...`;
  const r = await browser.runtime.sendMessage("rotate");
  if (r && r.ok) {
    ipEl.textContent = r.ip;
    locEl.textContent = "IP fraîche · France";
  } else {
    locEl.textContent = "Échec · Réessayez";
  }
  rotate.innerHTML = "🔄 Nouvelle IP française";
  rotate.disabled = false;
});

(async () => {
  let s = { active: false, ip: null };
  try {
    s = await browser.storage.local.get(["active", "ip"]);
  } catch (e) {}
  if (s.active) {
    setActive(s.ip);
  } else {
    setInactive();
  }
})();
