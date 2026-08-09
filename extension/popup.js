/*
 * IP Masker — Popup Controller
 * Live scraping · Fresh IP every time · Zero config
 */
const $ = id => document.getElementById(id);

const card = $("card"), dot = $("dot"), statusEl = $("status");
const ipEl = $("ip"), locEl = $("loc");
const toggle = $("toggle"), rotate = $("rotate");
const footer = $("footer");
let active = false;

function setActive(ip) {
  active = true;
  card.className = "card active";
  dot.className = "status-dot on";
  statusEl.textContent = "Protégé"; statusEl.className = "status-text on";
  ipEl.textContent = ip || "Protégé"; ipEl.className = "ip-display on";
  locEl.textContent = "IP masquée · France";
  toggle.textContent = "Désactiver le masquage";
  toggle.className = "btn btn-danger";
  toggle.disabled = false;
  rotate.classList.remove("hidden"); rotate.disabled = false;
  footer.classList.add("hidden");
}

function setInactive() {
  active = false;
  card.className = "card inactive";
  dot.className = "status-dot off";
  statusEl.textContent = "Inactif"; statusEl.className = "status-text off";
  ipEl.textContent = "—"; ipEl.className = "ip-display off";
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
    await new Promise(r => chrome.runtime.sendMessage("stop", r));
    setInactive();
  } else {
    setLoading("Scraping en direct...");
    const r = await new Promise(r2 => chrome.runtime.sendMessage("start", r2));
    if (r && r.ok) {
      setActive(r.ip);
    } else {
      ipEl.textContent = "Échec";
      ipEl.className = "ip-display off";
      locEl.textContent = "Aucun proxy FR trouvé · Réessayez";
      toggle.textContent = "Réessayer";
      toggle.className = "btn btn-primary";
      toggle.disabled = false;
    }
  }
});

rotate.addEventListener("click", async () => {
  rotate.disabled = true;
  rotate.innerHTML = `<span class="spinner"></span> Scraping...`;
  const r = await new Promise(r2 => chrome.runtime.sendMessage("rotate", r2));
  if (r && r.ok && r.ip) {
    ipEl.textContent = r.ip;
    locEl.textContent = "Nouvelle IP · France";
  }
  rotate.innerHTML = "🔄 Nouvelle IP française";
  rotate.disabled = false;
});

// Init
chrome.storage.local.get(["active", "ip"], d => {
  if (d.active) setActive(d.ip);
  else setInactive();
});

// Live IP refresh every 8s
setInterval(() => {
  if (active) {
    chrome.storage.local.get(["ip"], d => {
      if (d.ip && d.ip !== ipEl.textContent) ipEl.textContent = d.ip;
    });
  }
}, 8000);
