# FrenchIPMasker - Proxy Local (ixbrower) v2.1
# Fast startup with pre-loaded proxies + parallel testing
import customtkinter as ctk
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_scraper import FastProxyManager
from proxy_server import ForwardProxyServer

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FrenchIPMasker - Proxy")
        self.geometry("400x540")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")

        self.pm = FastProxyManager(on_update=self.on_progress)
        self.server = ForwardProxyServer(host="127.0.0.1", port=8080, proxy_manager=self.pm)
        self.active = False
        self._build()
        self._update_loop()

    def _build(self):
        ctk.CTkLabel(self, text="FrenchIPMasker", font=ctk.CTkFont(size=24, weight="bold"), text_color="#58a6ff").pack(pady=(22, 2))
        ctk.CTkLabel(self, text="Proxy Local · ixbrower 127.0.0.1:8080", font=ctk.CTkFont(size=11), text_color="#8b949e").pack()

        self.card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=14, border_width=1, border_color="#30363d")
        self.card.pack(pady=(18, 10), padx=22, fill="x")

        self.status_lbl = ctk.CTkLabel(self.card, text="○ Prêt", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f85149")
        self.status_lbl.pack(pady=(16, 6))

        self.ip_lbl = ctk.CTkLabel(self.card, text="—", font=ctk.CTkFont(size=20, weight="bold"), text_color="#c9d1d9")
        self.ip_lbl.pack()

        self.loc_lbl = ctk.CTkLabel(self.card, text="Proxy inactif", font=ctk.CTkFont(size=11), text_color="#8b949e")
        self.loc_lbl.pack(pady=(2, 8))

        self.progress_lbl = ctk.CTkLabel(self.card, text="", font=ctk.CTkFont(size=11), text_color="#58a6ff")
        self.progress_lbl.pack(pady=(0, 14))

        self.btn = ctk.CTkButton(self, text="Démarrer le proxy", font=ctk.CTkFont(size=14, weight="bold"),
            height=44, corner_radius=10, fg_color="#238636", hover_color="#2ea043", command=self._toggle)
        self.btn.pack(pady=(5, 6), padx=22, fill="x")

        self.rot_btn = ctk.CTkButton(self, text="Changer d'IP FR", font=ctk.CTkFont(size=12),
            height=36, corner_radius=10, fg_color="#21262d", hover_color="#30363d",
            border_width=1, border_color="#30363d", state="disabled", command=self._rotate)
        self.rot_btn.pack(pady=(0, 8), padx=22, fill="x")

        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10, border_width=1, border_color="#30363d")
        info.pack(pady=(5, 8), padx=22, fill="x")
        ctk.CTkLabel(info, text="Config ixbrower → 127.0.0.1 : 8080 (HTTP)", font=ctk.CTkFont(size=11), text_color="#8b949e").pack(pady=(10, 10))

        self.bottom = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10), text_color="#484f58")
        self.bottom.pack(side="bottom", pady=(0, 6))

    def _toggle(self):
        if self.active: self._stop()
        else: self._start()

    def _start(self):
        self.btn.configure(state="disabled", text="Recherche...")
        self.progress_lbl.configure(text="Test des proxys FR pré-chargés...")
        self.bottom.configure(text="Étape 1/2 : Test rapide...")

        def task():
            result = self.pm.start()
            if result:
                self.server.start()
                self.active = True
                self.after(0, self._on_started)
            else:
                self.after(0, self._on_failed)

        threading.Thread(target=task, daemon=True).start()

    def _stop(self):
        self.server.stop()
        self.active = False
        self._set_ui_stopped()

    def _rotate(self):
        if not self.active: return
        self.rot_btn.configure(state="disabled", text="...")
        def task():
            proxy = self.pm.rotate()
            self.after(0, self._on_rotated, proxy)
        threading.Thread(target=task, daemon=True).start()

    def on_progress(self, msg, data):
        self.after(0, self._update_progress, msg, data)

    def _update_progress(self, msg, data):
        if not self.active and not self.btn.cget("state") == "disabled":
            return
        done = data.get("done", 0)
        total = data.get("total", 0)
        found = data.get("found", 0)
        ready = data.get("ready", False)

        if ready:
            self.progress_lbl.configure(text=f"{found} proxys FR trouvés !")
        elif total > 0:
            self.progress_lbl.configure(text=f"Test : {done}/{total} — {found} FR trouvés")
        else:
            self.progress_lbl.configure(text=msg)

    def _set_ui_started(self):
        s = self.pm.get_status()
        self.status_lbl.configure(text="● Actif", text_color="#3fb950")
        self.ip_lbl.configure(text=s["current_ip"], text_color="#58a6ff")
        self.loc_lbl.configure(text="France (proxy HTTP)")
        self.btn.configure(text="Arrêter le proxy", fg_color="#da3633", hover_color="#f85149", state="normal")
        self.rot_btn.configure(state="normal")
        self.progress_lbl.configure(text=f"{s['working']} proxys FR dispos")
        self.bottom.configure(text=f"Proxy : {s['current_proxy']}")

    def _set_ui_stopped(self):
        self.status_lbl.configure(text="○ Arrêté", text_color="#f85149")
        self.ip_lbl.configure(text="—", text_color="#c9d1d9")
        self.loc_lbl.configure(text="Proxy inactif")
        self.btn.configure(text="Démarrer le proxy", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.rot_btn.configure(state="disabled")
        self.progress_lbl.configure(text="")
        self.bottom.configure(text="")

    def _on_started(self): self._set_ui_started()
    def _on_failed(self):
        self.status_lbl.configure(text="✕ Aucun proxy FR", text_color="#f85149")
        self.ip_lbl.configure(text="Échec", text_color="#c9d1d9")
        self.loc_lbl.configure(text="Réessayez")
        self.btn.configure(text="Démarrer le proxy", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.progress_lbl.configure(text="Vérifiez votre connexion internet")
        self.bottom.configure(text="")

    def _on_rotated(self, p):
        s = self.pm.get_status()
        self.ip_lbl.configure(text=s["current_ip"], text_color="#58a6ff")
        self.rot_btn.configure(state="normal", text="Changer d'IP FR")
        self.bottom.configure(text=f"Proxy : {s['current_proxy']}")

    def _update_loop(self):
        if self.active:
            s = self.pm.get_status()
            self.progress_lbl.configure(text=f"{s['working']} proxys FR dispos")
        self.after(8000, self._update_loop)

if __name__ == "__main__":
    App().mainloop()
