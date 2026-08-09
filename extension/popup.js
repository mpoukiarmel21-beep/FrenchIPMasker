// Ultra-minimal popup — ON/OFF + IP display
const $ = id => document.getElementById(id);
const bg = chrome.runtime;
let active = false;

const dot = $("dot"), ip = $("ip"), label = $("label");
const toggle = $("toggle"), rotateBtn = $("rotate"), msg = $("msg");

function updateUI(d) {
  active = !!d.active;
  if (active) {
    dot.textContent = "●"; dot.className = "dot on";
    ip.textContent = d.ip || "Protégé";
    label.textContent = "IP masquée";
    toggle.textContent = "Désactiver le masquage";
    toggle.className = "btn btn-off"; toggle.disabled = false;
    rotateBtn.classList.remove("hidden"); rotateBtn.disabled = false;
    msg.classList.add("hidden");
  } else {
    dot.textContent = "●"; dot.className = "dot off";
    ip.textContent = "—";
    label.textContent = "Inactif";
    toggle.textContent = "Activer le masquage";
    toggle.className = "btn btn-on"; toggle.disabled = false;
    rotateBtn.classList.add("hidden");
    msg.classList.remove("hidden");
  }
}

toggle.addEventListener("click", async () => {
  toggle.disabled = true;
  if (active) {
    toggle.textContent = "Arrêt...";
    await new Promise(r => bg.sendMessage("stop", r));
    updateUI({ active: false });
  } else {
    toggle.textContent = "Recherche...";
    const r = await new Promise(r2 => bg.sendMessage("start", r2));
    updateUI({ active: r.ok, ip: r.ip });
    if (!r.ok) {
      ip.textContent = "Échec";
      label.textContent = "Réessayez";
    }
  }
});

rotateBtn.addEventListener("click", async () => {
  rotateBtn.disabled = true; rotateBtn.textContent = "...";
  await new Promise(r => bg.sendMessage("rotate", r));
  const s = await new Promise(r => bg.sendMessage("status", r));
  updateUI(s);
  rotateBtn.textContent = "🔄 Changer d'IP";
});

// Init
chrome.storage.local.get(["active","ip"], d => updateUI(d));

// Refresh every 10s
setInterval(() => {
  chrome.storage.local.get(["active","ip"], d => { if (active) ip.textContent = d.ip || "Protégé"; });
}, 10000);
