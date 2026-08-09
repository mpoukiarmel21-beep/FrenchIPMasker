const $ = id => document.getElementById(id);
const bg = chrome.runtime;
let active = false;

const dot = $("dot"), ip = $("ip"), label = $("label");
const toggle = $("toggle"), rotateBtn = $("rotate"), msg = $("msg");

function ui(d) {
  active = !!d.active;
  if (active) {
    dot.textContent = "●"; dot.className = "dot on";
    ip.textContent = d.ip || "Protégé";
    label.textContent = "IP masquée · Live";
    toggle.textContent = "Désactiver";
    toggle.className = "btn btn-off"; toggle.disabled = false;
    rotateBtn.classList.remove("hidden"); rotateBtn.disabled = false;
    msg.classList.add("hidden");
  } else {
    dot.textContent = "●"; dot.className = "dot off";
    ip.textContent = "—"; label.textContent = "Inactif";
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
    ui({ active: false });
  } else {
    toggle.textContent = "Scraping live...";
    const r = await new Promise(r2 => bg.sendMessage("start", r2));
    if (r.ok) {
      ui({ active: true, ip: r.ip });
    } else {
      ip.textContent = "Aucun proxy";
      label.textContent = "Réessayez";
      ui({ active: false });
    }
  }
});

rotateBtn.addEventListener("click", async () => {
  rotateBtn.disabled = true; rotateBtn.textContent = "Scraping...";
  const r = await new Promise(r2 => bg.sendMessage("rotate", r2));
  if (r.ok) { ip.textContent = r.ip; } 
  rotateBtn.textContent = "🔄 Nouvelle IP (live scraping)";
  rotateBtn.disabled = false;
});

chrome.storage.local.get(["active","ip"], d => ui(d));
setInterval(() => {
  chrome.storage.local.get(["active","ip"], d => { if (active) ip.textContent = d.ip || "Protégé"; });
}, 8000);
