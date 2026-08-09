# FrenchIPMasker - Version Proxy Local
# Runs a local HTTP proxy server using free French proxies
# Configure ixbrower to use 127.0.0.1:8080

import customtkinter as ctk
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proxy_server import ForwardProxyServer
from proxy_scraper import ProxyManager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ProxyMaskerLocal(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FrenchIPMasker - Proxy Local v1.0")
        self.geometry("420x560")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")

        self.pm = ProxyManager()
        self.server = ForwardProxyServer(host="127.0.0.1", port=8080, proxy_manager=self.pm)
        self.active = False

        self.build_ui()
        self.update_loop()

    def build_ui(self):
        # Title
        ctk.CTkLabel(self, text="FrenchIPMasker",
            font=ctk.CTkFont(size=26, weight="bold"), text_color="#58a6ff"
        ).pack(pady=(25, 2))

        ctk.CTkLabel(self, text="Proxy Local · ixbrower compatible",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        ).pack()

        # Status card
        self.card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=16, border_width=1, border_color="#30363d")
        self.card.pack(pady=(20, 12), padx=25, fill="x")

        self.status_indicator = ctk.CTkLabel(self.card, text="○ Arrêté",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#f85149")
        self.status_indicator.pack(pady=(18, 8))

        self.ip_display = ctk.CTkLabel(self.card, text="—",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#c9d1d9")
        self.ip_display.pack()

        self.loc_display = ctk.CTkLabel(self.card, text="Proxy non actif",
            font=ctk.CTkFont(size=12), text_color="#8b949e")
        self.loc_display.pack(pady=(2, 18))

        # Toggle
        self.toggle_btn = ctk.CTkButton(self, text="Démarrer le proxy",
            font=ctk.CTkFont(size=15, weight="bold"), height=48, corner_radius=12,
            fg_color="#238636", hover_color="#2ea043", command=self.toggle)
        self.toggle_btn.pack(pady=(5, 8), padx=25, fill="x")

        # Change IP
        self.change_btn = ctk.CTkButton(self, text="Changer de proxy FR",
            font=ctk.CTkFont(size=13), height=40, corner_radius=12,
            fg_color="#21262d", hover_color="#30363d", border_width=1,
            border_color="#30363d", state="disabled", command=self.rotate)
        self.change_btn.pack(pady=(0, 10), padx=25, fill="x")

        # Info card
        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d")
        info.pack(pady=(5, 10), padx=25, fill="x")

        ctk.CTkLabel(info, text="Configuration ixbrower",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#c9d1d9"
        ).pack(pady=(12, 5))

        ctk.CTkLabel(info, text="Proxy HTTP : 127.0.0.1 : 8080",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        ).pack()

        ctk.CTkLabel(info, text="Type : HTTP / HTTPS",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        ).pack(pady=(0, 12))

        # Stats
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(pady=(5, 5), padx=25, fill="x")

        self.proxy_count = ctk.CTkLabel(self.stats_frame,
            text="Proxys FR disponibles : ...", font=ctk.CTkFont(size=11), text_color="#484f58")
        self.proxy_count.pack(anchor="w")

        self.proxy_source = ctk.CTkLabel(self.stats_frame,
            text="Proxy actif : —", font=ctk.CTkFont(size=11), text_color="#484f58")
        self.proxy_source.pack(anchor="w")

        # Progress
        self.progress = ctk.CTkProgressBar(self, height=3, corner_radius=0, fg_color="#161b22", progress_color="#58a6ff")
        self.progress.pack(side="bottom", fill="x")
        self.progress.set(0)

        self.status_text = ctk.CTkLabel(self, text="Prêt · Cliquez Démarrer",
            font=ctk.CTkFont(size=10), text_color="#484f58")
        self.status_text.pack(side="bottom", pady=(0, 8))

    def toggle(self):
        if self.active:
            self.stop()
        else:
            self.start()

    def start(self):
        self.toggle_btn.configure(state="disabled", text="Recherche de proxys FR...")
        self.progress.start()
        self.status_text.configure(text="Scraping + test des proxys français...")

        def task():
            self.pm.fetch_all()
            self.pm.test_french(max_test=60)
            proxy = self.pm.get_best()
            if proxy:
                self.server.start()
                self.active = True
                self.after(0, self._on_started)
            else:
                self.after(0, self._on_failed)

        threading.Thread(target=task, daemon=True).start()

    def stop(self):
        self.server.stop()
        self.active = False
        self._on_stopped()

    def rotate(self):
        if not self.active: return
        self.change_btn.configure(state="disabled", text="Rotation...")
        self.progress.start()

        def task():
            self.pm.refresh_background()
            time.sleep(2)
            proxy = self.pm.get_best()
            self.after(0, self._on_rotated, proxy)

        threading.Thread(target=task, daemon=True).start()

    def _on_started(self):
        self.progress.stop()
        self.progress.set(1)
        self.status_indicator.configure(text="● Actif", text_color="#3fb950")
        status = self.pm.get_status()
        self.ip_display.configure(text=status["current_ip"], text_color="#58a6ff")
        self.loc_display.configure(text="France (proxy HTTP)")
        self.toggle_btn.configure(text="Arrêter le proxy", fg_color="#da3633", hover_color="#f85149", state="normal")
        self.change_btn.configure(state="normal")
        self.proxy_count.configure(text=f"Proxys FR dispos : {status['working_french']}")
        self.proxy_source.configure(text=f"Proxy actif : {status['current_proxy'] or '—'}")
        self.status_text.configure(text="Proxy actif · Configurer ixbrower sur 127.0.0.1:8080")

    def _on_stopped(self):
        self.progress.stop()
        self.progress.set(0)
        self.status_indicator.configure(text="○ Arrêté", text_color="#f85149")
        self.ip_display.configure(text="—", text_color="#c9d1d9")
        self.loc_display.configure(text="Proxy non actif")
        self.toggle_btn.configure(text="Démarrer le proxy", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.change_btn.configure(state="disabled")
        self.proxy_source.configure(text="Proxy actif : —")
        self.status_text.configure(text="Prêt · Cliquez Démarrer")

    def _on_failed(self):
        self.progress.stop()
        self.progress.set(0)
        self.status_indicator.configure(text="✕ Erreur", text_color="#f85149")
        self.ip_display.configure(text="Aucun proxy FR trouvé", text_color="#c9d1d9")
        self.loc_display.configure(text="Réessayez")
        self.toggle_btn.configure(text="Démarrer le proxy", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.status_text.configure(text="Aucun proxy français disponible")

    def _on_rotated(self, proxy):
        self.progress.stop()
        self.progress.set(1)
        status = self.pm.get_status()
        self.ip_display.configure(text=status["current_ip"], text_color="#58a6ff")
        self.proxy_source.configure(text=f"Proxy actif : {status['current_proxy'] or '—'}")
        self.change_btn.configure(state="normal", text="Changer de proxy FR")
        self.proxy_count.configure(text=f"Proxys FR dispos : {status['working_french']}")
        self.status_text.configure(text="Proxy FR changé")

    def update_loop(self):
        if self.active:
            try:
                status = self.pm.get_status()
                self.proxy_count.configure(text=f"Proxys FR dispos : {status['working_french']}")
            except:
                pass
        self.after(15000, self.update_loop)

if __name__ == "__main__":
    app = ProxyMaskerLocal()
    app.mainloop()
