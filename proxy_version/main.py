# FrenchIPMasker - Proxy Local v3.0 (Infinite IPs)
import customtkinter as ctk, threading, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_scraper import InfiniteProxyPool
from proxy_server import ForwardProxyServer

ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FrenchIPMasker - Proxy ∞")
        self.geometry("400x560")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")
        self.pool = InfiniteProxyPool(on_update=self._on_pool)
        self.server = ForwardProxyServer(host="127.0.0.1", port=8080, proxy_manager=self, transparent=True)
        self.active = False
        self._build()
        self._loop()

    def get_best(self):
        if self.pool._current: return self.pool._current["proxy"]
        return None

    def _build(self):
        ctk.CTkLabel(self, text="FrenchIPMasker ∞", font=ctk.CTkFont(size=24, weight="bold"), text_color="#58a6ff").pack(pady=(20, 2))
        ctk.CTkLabel(self, text="Proxy Local · ixbrower · IPs illimitées", font=ctk.CTkFont(size=11), text_color="#8b949e").pack()

        self.card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=14, border_width=1, border_color="#30363d")
        self.card.pack(pady=(16, 8), padx=20, fill="x")

        self.status_lbl = ctk.CTkLabel(self.card, text="○ Prêt", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f85149")
        self.status_lbl.pack(pady=(14, 6))

        self.ip_lbl = ctk.CTkLabel(self.card, text="—", font=ctk.CTkFont(size=22, weight="bold"), text_color="#c9d1d9")
        self.ip_lbl.pack()

        self.loc_lbl = ctk.CTkLabel(self.card, text="Proxy inactif", font=ctk.CTkFont(size=11), text_color="#8b949e")
        self.loc_lbl.pack(pady=(2, 2))

        self.pool_lbl = ctk.CTkLabel(self.card, text="∞ IPs disponibles", font=ctk.CTkFont(size=11), text_color="#58a6ff")
        self.pool_lbl.pack(pady=(0, 14))

        self.btn = ctk.CTkButton(self, text="Démarrer le proxy ∞", font=ctk.CTkFont(size=14, weight="bold"),
            height=46, corner_radius=10, fg_color="#238636", hover_color="#2ea043", command=self._toggle)
        self.btn.pack(pady=(4, 4), padx=20, fill="x")

        self.rot_btn = ctk.CTkButton(self, text="🔄 Changer d'IP (instantané)", font=ctk.CTkFont(size=12),
            height=38, corner_radius=10, fg_color="#21262d", hover_color="#30363d",
            border_width=1, border_color="#30363d", state="disabled", command=self._rotate)
        self.rot_btn.pack(pady=(0, 4), padx=20, fill="x")

        self.trans_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.trans_frame.pack(pady=(0, 2), padx=20, fill="x")
        self.trans_var = ctk.BooleanVar(value=True)
        self.trans_switch = ctk.CTkSwitch(self.trans_frame, text="Mode transparent (Internet direct si proxy KO)",
            variable=self.trans_var, command=self._toggle_transparent,
            fg_color="#30363d", progress_color="#58a6ff")
        self.trans_switch.pack(side="left")

        self.auto_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.auto_frame.pack(pady=(2, 6), padx=20, fill="x")
        self.auto_var = ctk.BooleanVar(value=False)
        self.auto_switch = ctk.CTkSwitch(self.auto_frame, text="Rotation auto (30s)", variable=self.auto_var,
            command=self._toggle_auto, fg_color="#30363d", progress_color="#238636", state="disabled")
        self.auto_switch.pack(side="left")

        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10, border_width=1, border_color="#30363d")
        info.pack(pady=(4, 6), padx=20, fill="x")
        ctk.CTkLabel(info, text="ixbrower → 127.0.0.1 : 8080 (HTTP)", font=ctk.CTkFont(size=11), text_color="#8b949e").pack(pady=(8, 8))

        self.bottom = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10), text_color="#484f58")
        self.bottom.pack(side="bottom", pady=(0, 6))

    def _toggle(self):
        if self.active: self._stop()
        else: self._start()

    def _start(self):
        self.btn.configure(state="disabled", text="Analyse des proxys FR...")
        self.pool_lbl.configure(text="Recherche de proxys...")
        def task():
            ok = self.pool.start()
            if ok:
                self.server.start()
                self.active = True
            self.after(0, self._on_started if ok else self._on_failed)
        threading.Thread(target=task, daemon=True).start()

    def _stop(self):
        self.pool.stop()
        self.server.stop()
        self.active = False
        self.auto_var.set(False)
        self._set_ui("○ Prêt", "—", "Proxy inactif", "#f85149")
        self.btn.configure(text="Démarrer le proxy ∞", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.rot_btn.configure(state="disabled")
        self.auto_switch.configure(state="disabled")
        self.pool_lbl.configure(text="∞ IPs disponibles")
        self.bottom.configure(text="")

    def _rotate(self):
        if not self.active: return
        p = self.pool.rotate()
        if p:
            s = self.pool.get_status()
            self.ip_lbl.configure(text=s["ip"], text_color="#58a6ff")
            self.loc_lbl.configure(text=f"France · {s['latency']}ms")
            self.pool_lbl.configure(text=f"Pool : {s['ready']} proxys FR | ∞ rotations")
            self.bottom.configure(text=f"IP: {s['proxy']}")

    def _toggle_auto(self):
        if self.auto_var.get():
            self._auto_rotate()

    def _toggle_transparent(self):
        self.server.transparent = self.trans_var.get()
        self.bottom.configure(text=f"Mode transparent : {'ON' if self.trans_var.get() else 'OFF'} (fallback si aucun proxy)")

    def _auto_rotate(self):
        if not self.active or not self.auto_var.get(): return
        self._rotate()
        self.after(30000, self._auto_rotate)

    def _on_pool(self, msg, data):
        self.after(0, self._update_pool, msg, data)

    def _update_pool(self, msg, data):
        if msg == "ready":
            self.pool_lbl.configure(text=f"Pool : {data['ready']} proxys FR | ∞ rotations")
            self.bottom.configure(text=f"{data['total']} IPs collectées · Rotation instantanée")
        elif msg == "found":
            self.pool_lbl.configure(text=f"✓ {data['ip']} → Pool: {data['ready']}")
        elif msg == "testing":
            self.pool_lbl.configure(text=f"Test... {data['tested']}/{data['total']} | {data['ready']} FR")
        elif msg == "scraping":
            self.pool_lbl.configure(text="Scraping web...")
        elif msg == "refresh":
            self.pool_lbl.configure(text=f"Pool: {data['ready']} FR | {data['total']} total")

    def _set_ui(self, status, ip, loc, color):
        self.status_lbl.configure(text=status, text_color=color)
        self.ip_lbl.configure(text=ip, text_color="#58a6ff" if self.active else "#c9d1d9")
        self.loc_lbl.configure(text=loc)

    def _on_started(self):
        s = self.pool.get_status()
        self._set_ui("● Actif ∞", s["ip"], f"France · {s['latency']}ms", "#3fb950")
        self.btn.configure(text="Arrêter le proxy", fg_color="#da3633", hover_color="#f85149", state="normal")
        self.rot_btn.configure(state="normal")
        self.auto_switch.configure(state="normal")
        self.pool_lbl.configure(text=f"Pool : {s['ready']} proxys FR | ∞ rotations")
        self.bottom.configure(text=f"IP: {s['proxy']} · {s['total']} IPs disponibles")

    def _on_failed(self):
        self.status_lbl.configure(text="✕ Aucun proxy FR", text_color="#f85149")
        self.ip_lbl.configure(text="Échec", text_color="#c9d1d9")
        self.btn.configure(text="Réessayer", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.pool_lbl.configure(text="Vérifiez votre connexion")

    def _loop(self):
        if self.active:
            s = self.pool.get_status()
            self.pool_lbl.configure(text=f"Pool : {s['ready']} FR | {s['total']} total | ∞")
        self.after(5000, self._loop)

if __name__ == "__main__":
    App().mainloop()
