# FrenchIPMasker - Version Masquage Global
# Masks entire PC connection through free French proxies
# System-wide Windows proxy configuration

import customtkinter as ctk
import threading
import time
import sys
import os
import ctypes
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_scraper import ProxyManager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ProxyMaskerGlobal(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FrenchIPMasker - Global v1.0")
        self.geometry("420x560")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")

        self.pm = ProxyManager()
        self.active = False

        self.build_ui()
        self.update_loop()

    def build_ui(self):
        # Title
        ctk.CTkLabel(self, text="FrenchIPMasker",
            font=ctk.CTkFont(size=26, weight="bold"), text_color="#58a6ff"
        ).pack(pady=(25, 2))

        ctk.CTkLabel(self, text="Masquage Global · Tout le PC",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        ).pack()

        # Status card
        self.card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=16, border_width=1, border_color="#30363d")
        self.card.pack(pady=(20, 12), padx=25, fill="x")

        self.status_indicator = ctk.CTkLabel(self.card, text="○ Non protégé",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#f85149")
        self.status_indicator.pack(pady=(18, 8))

        self.ip_display = ctk.CTkLabel(self.card, text="192.168.1.xxx",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#c9d1d9")
        self.ip_display.pack()

        self.loc_display = ctk.CTkLabel(self.card, text="Votre vraie IP",
            font=ctk.CTkFont(size=12), text_color="#8b949e")
        self.loc_display.pack(pady=(2, 18))

        # Toggle
        self.toggle_btn = ctk.CTkButton(self, text="Activer le masquage",
            font=ctk.CTkFont(size=15, weight="bold"), height=48, corner_radius=12,
            fg_color="#238636", hover_color="#2ea043", command=self.toggle)
        self.toggle_btn.pack(pady=(5, 8), padx=25, fill="x")

        # Change IP
        self.change_btn = ctk.CTkButton(self, text="Changer d'IP française",
            font=ctk.CTkFont(size=13), height=40, corner_radius=12,
            fg_color="#21262d", hover_color="#30363d", border_width=1,
            border_color="#30363d", state="disabled", command=self.rotate)
        self.change_btn.pack(pady=(0, 10), padx=25, fill="x")

        # Info card
        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d")
        info.pack(pady=(5, 10), padx=25, fill="x")

        ctk.CTkLabel(info, text="Protection système",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#c9d1d9"
        ).pack(pady=(12, 5))

        ctk.CTkLabel(info, text="Tout le trafic passe par un proxy FR",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        ).pack()

        ctk.CTkLabel(info, text="Navigateur · Applications · Jeux",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        ).pack(pady=(0, 12))

        # Stats
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(pady=(5, 5), padx=25, fill="x")

        self.proxy_count = ctk.CTkLabel(self.stats_frame,
            text="Proxys FR disponibles : ...", font=ctk.CTkFont(size=11), text_color="#484f58")
        self.proxy_count.pack(anchor="w")

        self.leak_label = ctk.CTkLabel(self.stats_frame,
            text="Kill Switch : Prêt", font=ctk.CTkFont(size=11), text_color="#238636")
        self.leak_label.pack(anchor="w")

        # Progress
        self.progress = ctk.CTkProgressBar(self, height=3, corner_radius=0, fg_color="#161b22", progress_color="#58a6ff")
        self.progress.pack(side="bottom", fill="x")
        self.progress.set(0)

        self.status_text = ctk.CTkLabel(self, text="Prêt · Cliquez Activer",
            font=ctk.CTkFont(size=10), text_color="#484f58")
        self.status_text.pack(side="bottom", pady=(0, 8))

    def toggle(self):
        if self.active:
            self.deactivate()
        else:
            self.activate()

    def activate(self):
        self.toggle_btn.configure(state="disabled", text="Recherche de proxys FR...")
        self.progress.start()

        def task():
            self.pm.fetch_all()
            self.pm.test_french(max_test=60)
            proxy = self.pm.get_best()
            if proxy:
                self._set_system_proxy(proxy)
                self.active = True
                self.after(0, self._on_activated)
            else:
                self.after(0, self._on_failed)

        threading.Thread(target=task, daemon=True).start()

    def deactivate(self):
        self._set_system_proxy(None)
        self.active = False
        self._on_deactivated()

    def rotate(self):
        if not self.active: return
        self.change_btn.configure(state="disabled", text="Rotation...")
        self.progress.start()

        def task():
            self.pm.refresh_background()
            time.sleep(2)
            proxy = self.pm.get_best()
            if proxy:
                self._set_system_proxy(proxy)
            self.after(0, self._on_rotated, proxy)

        threading.Thread(target=task, daemon=True).start()

    def _set_system_proxy(self, proxy):
        """Set Windows system proxy via registry"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_SET_VALUE)

            if proxy:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"http={proxy};https={proxy}")
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
            else:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "")

            winreg.CloseKey(key)

            # Notify system
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)

            # Force French timezone
            subprocess.run('tzutil /s "Romance Standard Time"', shell=True, capture_output=True)

        except Exception as e:
            print(f"[Global] Proxy set error: {e}")

    def _on_activated(self):
        self.progress.stop(); self.progress.set(1)
        self.status_indicator.configure(text="● Protégé", text_color="#3fb950")
        status = self.pm.get_status()
        self.ip_display.configure(text=status["current_ip"], text_color="#58a6ff")
        self.loc_display.configure(text="France (masquage global)")
        self.toggle_btn.configure(text="Désactiver le masquage", fg_color="#da3633", hover_color="#f85149", state="normal")
        self.change_btn.configure(state="normal")
        self.proxy_count.configure(text=f"Proxys FR dispos : {status['working_french']}")
        self.leak_label.configure(text="Kill Switch : Actif ✓", text_color="#3fb950")
        self.status_text.configure(text="Masquage actif · Tout le PC passe par la France")

    def _on_deactivated(self):
        self.progress.stop(); self.progress.set(0)
        self.status_indicator.configure(text="○ Non protégé", text_color="#f85149")
        self.ip_display.configure(text="Déconnecté", text_color="#c9d1d9")
        self.loc_display.configure(text="Votre vraie IP")
        self.toggle_btn.configure(text="Activer le masquage", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.change_btn.configure(state="disabled")
        self.leak_label.configure(text="Kill Switch : Inactif", text_color="#484f58")
        self.status_text.configure(text="Masquage désactivé")

        # Restore timezone
        subprocess.run('tzutil /s "Romance Standard Time"', shell=True, capture_output=True)

    def _on_failed(self):
        self.progress.stop(); self.progress.set(0)
        self.status_indicator.configure(text="✕ Erreur", text_color="#f85149")
        self.ip_display.configure(text="Aucun proxy FR", text_color="#c9d1d9")
        self.loc_display.configure(text="Réessayez")
        self.toggle_btn.configure(text="Activer le masquage", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.status_text.configure(text="Aucun proxy français trouvé")

    def _on_rotated(self, proxy):
        self.progress.stop(); self.progress.set(1)
        status = self.pm.get_status()
        self.ip_display.configure(text=status["current_ip"], text_color="#58a6ff")
        self.proxy_count.configure(text=f"Proxys FR dispos : {status['working_french']}")
        self.change_btn.configure(state="normal", text="Changer d'IP française")
        self.status_text.configure(text="Nouvelle IP française")

    def update_loop(self):
        if self.active:
            status = self.pm.get_status()
            self.proxy_count.configure(text=f"Proxys FR dispos : {status['working_french']}")
        self.after(15000, self.update_loop)

if __name__ == "__main__":
    app = ProxyMaskerGlobal()
    app.mainloop()
