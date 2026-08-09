# FrenchIPMasker - Global v2.1 (system-wide)
# Fast startup with pre-loaded proxies + parallel testing
import customtkinter as ctk
import threading, sys, os, winreg, ctypes, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_scraper import FastProxyManager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FrenchIPMasker - Global")
        self.geometry("400x540")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")

        self.pm = FastProxyManager(on_update=self.on_progress)
        self.active = False
        self._build()
        self._update_loop()

    def _build(self):
        ctk.CTkLabel(self, text="FrenchIPMasker", font=ctk.CTkFont(size=24, weight="bold"), text_color="#58a6ff").pack(pady=(22, 2))
        ctk.CTkLabel(self, text="Masquage Global · Tout le PC", font=ctk.CTkFont(size=11), text_color="#8b949e").pack()

        self.card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=14, border_width=1, border_color="#30363d")
        self.card.pack(pady=(18, 10), padx=22, fill="x")

        self.status_lbl = ctk.CTkLabel(self.card, text="○ Non protégé", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f85149")
        self.status_lbl.pack(pady=(16, 6))

        self.ip_lbl = ctk.CTkLabel(self.card, text="192.168.x.x", font=ctk.CTkFont(size=20, weight="bold"), text_color="#c9d1d9")
        self.ip_lbl.pack()

        self.loc_lbl = ctk.CTkLabel(self.card, text="Votre vraie IP", font=ctk.CTkFont(size=11), text_color="#8b949e")
        self.loc_lbl.pack(pady=(2, 8))

        self.progress_lbl = ctk.CTkLabel(self.card, text="", font=ctk.CTkFont(size=11), text_color="#58a6ff")
        self.progress_lbl.pack(pady=(0, 14))

        self.btn = ctk.CTkButton(self, text="Activer le masquage", font=ctk.CTkFont(size=14, weight="bold"),
            height=44, corner_radius=10, fg_color="#238636", hover_color="#2ea043", command=self._toggle)
        self.btn.pack(pady=(5, 6), padx=22, fill="x")

        self.rot_btn = ctk.CTkButton(self, text="Changer d'IP française", font=ctk.CTkFont(size=12),
            height=36, corner_radius=10, fg_color="#21262d", hover_color="#30363d",
            border_width=1, border_color="#30363d", state="disabled", command=self._rotate)
        self.rot_btn.pack(pady=(0, 8), padx=22, fill="x")

        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10, border_width=1, border_color="#30363d")
        info.pack(pady=(5, 8), padx=22, fill="x")
        ctk.CTkLabel(info, text="Navigateur · Applications · Jeux\nTout le trafic passe par la France", font=ctk.CTkFont(size=11), text_color="#8b949e").pack(pady=(10, 10))

        self.bottom = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10), text_color="#484f58")
        self.bottom.pack(side="bottom", pady=(0, 6))

    def _toggle(self):
        if self.active: self._deactivate()
        else: self._activate()

    def _activate(self):
        self.btn.configure(state="disabled", text="Recherche...")
        self.progress_lbl.configure(text="Test des proxys FR pré-chargés...")
        def task():
            r = self.pm.start()
            if r:
                p = self.pm.current["proxy"]
                self._set_proxy(p)
                self.active = True
                self.after(0, self._on_started)
            else:
                self.after(0, self._on_failed)
        threading.Thread(target=task, daemon=True).start()

    def _deactivate(self):
        self._set_proxy(None)
        self.active = False
        self._set_ui_stopped()

    def _rotate(self):
        if not self.active: return
        self.rot_btn.configure(state="disabled", text="...")
        def task():
            p = self.pm.rotate()
            if p: self._set_proxy(p["proxy"])
            self.after(0, self._on_rotated)
        threading.Thread(target=task, daemon=True).start()

    def _set_proxy(self, proxy):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_SET_VALUE)
            if proxy:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"http={proxy};https={proxy}")
            else:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
            if proxy:
                subprocess.run('tzutil /s "Romance Standard Time"', shell=True, capture_output=True)
        except Exception as e:
            print(f"Proxy error: {e}")

    def on_progress(self, msg, data):
        self.after(0, self._update_progress, msg, data)

    def _update_progress(self, msg, data):
        if not self.active and not self.btn.cget("state") == "disabled": return
        d, t, f = data.get("done", 0), data.get("total", 0), data.get("found", 0)
        if data.get("ready"):
            self.progress_lbl.configure(text=f"{f} proxys FR trouvés !")
        elif t > 0:
            self.progress_lbl.configure(text=f"Test : {d}/{t} — {f} FR trouvés")
        else:
            self.progress_lbl.configure(text=msg)

    def _set_ui_started(self):
        s = self.pm.get_status()
        self.status_lbl.configure(text="● Protégé", text_color="#3fb950")
        self.ip_lbl.configure(text=s["current_ip"], text_color="#58a6ff")
        self.loc_lbl.configure(text="France (global)")
        self.btn.configure(text="Désactiver", fg_color="#da3633", hover_color="#f85149", state="normal")
        self.rot_btn.configure(state="normal")
        self.progress_lbl.configure(text=f"{s['working']} proxys FR dispos")
        self.bottom.configure(text=f"Proxy : {s['current_proxy']} · TZ : Europe/Paris")

    def _set_ui_stopped(self):
        self.status_lbl.configure(text="○ Non protégé", text_color="#f85149")
        self.ip_lbl.configure(text="Déconnecté", text_color="#c9d1d9")
        self.loc_lbl.configure(text="Votre vraie IP")
        self.btn.configure(text="Activer le masquage", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.rot_btn.configure(state="disabled")
        self.progress_lbl.configure(text="")
        self.bottom.configure(text="")

    def _on_started(self): self._set_ui_started()
    def _on_failed(self):
        self.status_lbl.configure(text="✕ Aucun proxy FR", text_color="#f85149")
        self.ip_lbl.configure(text="Échec", text_color="#c9d1d9")
        self.loc_lbl.configure(text="Réessayez")
        self.btn.configure(text="Activer le masquage", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.progress_lbl.configure(text="Vérifiez votre connexion internet")
    def _on_rotated(self):
        s = self.pm.get_status()
        self.ip_lbl.configure(text=s["current_ip"])
        self.rot_btn.configure(state="normal", text="Changer d'IP française")
        self.bottom.configure(text=f"Proxy : {s['current_proxy']}")

    def _update_loop(self):
        if self.active:
            s = self.pm.get_status()
            self.progress_lbl.configure(text=f"{s['working']} proxys FR dispos")
        self.after(8000, self._update_loop)

if __name__ == "__main__":
    App().mainloop()
