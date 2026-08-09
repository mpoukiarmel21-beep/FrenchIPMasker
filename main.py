# FrenchIPMasker - Main Application
# Dark modern UI with CustomTkinter, Tor integration, French IP masking

import customtkinter as ctk
import threading
import time
import sys
import os
from tor_manager import TorManager
from proxy_scraper import ProxyScraper
from network import NetworkGuard

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FrenchIPMasker(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FrenchIPMasker")
        self.geometry("420x560")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")

        self.tor = TorManager()
        self.scraper = ProxyScraper()
        self.guard = NetworkGuard()
        self.protected = False
        self.current_ip = "..."
        self.ip_location = "..."

        self.build_ui()
        self.update_loop()

    def build_ui(self):
        # Title
        self.title_label = ctk.CTkLabel(
            self, text="FrenchIPMasker",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#58a6ff"
        )
        self.title_label.pack(pady=(25, 5))

        self.flag_label = ctk.CTkLabel(
            self, text="IP masking · France",
            font=ctk.CTkFont(size=13),
            text_color="#8b949e"
        )
        self.flag_label.pack()

        # Status card
        self.status_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=16, border_width=1, border_color="#30363d")
        self.status_frame.pack(pady=(20, 15), padx=25, fill="x")

        self.status_indicator = ctk.CTkLabel(
            self.status_frame, text="○  Non protégé",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f85149"
        )
        self.status_indicator.pack(pady=(18, 8))

        self.ip_display = ctk.CTkLabel(
            self.status_frame, text="192.168.1.xxx",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#c9d1d9"
        )
        self.ip_display.pack()

        self.location_display = ctk.CTkLabel(
            self.status_frame, text="Votre vraie IP",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e"
        )
        self.location_display.pack(pady=(2, 18))

        # Toggle button
        self.toggle_btn = ctk.CTkButton(
            self, text="Activer la protection",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=48,
            corner_radius=12,
            fg_color="#238636",
            hover_color="#2ea043",
            command=self.toggle_protection
        )
        self.toggle_btn.pack(pady=(5, 8), padx=25, fill="x")

        # Change IP button
        self.change_btn = ctk.CTkButton(
            self, text="Nouvelle IP française",
            font=ctk.CTkFont(size=13),
            height=40,
            corner_radius=12,
            fg_color="#21262d",
            hover_color="#30363d",
            border_width=1,
            border_color="#30363d",
            state="disabled",
            command=self.change_ip
        )
        self.change_btn.pack(pady=(0, 15), padx=25, fill="x")

        # Info section
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(pady=(5, 10), padx=25, fill="x")

        self.source_label = ctk.CTkLabel(
            self.info_frame, text="Source : Tor + Proxys FR",
            font=ctk.CTkFont(size=11),
            text_color="#484f58"
        )
        self.source_label.pack(anchor="w")

        self.real_ip_label = ctk.CTkLabel(
            self.info_frame, text="IP réelle : 192.168.1.xxx (masquée)",
            font=ctk.CTkFont(size=11),
            text_color="#484f58"
        )
        self.real_ip_label.pack(anchor="w")

        self.leak_label = ctk.CTkLabel(
            self.info_frame, text="Fuites : Aucune ✓",
            font=ctk.CTkFont(size=11),
            text_color="#238636"
        )
        self.leak_label.pack(anchor="w")

        # Progress bar
        self.progress = ctk.CTkProgressBar(self, height=3, corner_radius=0, fg_color="#161b22", progress_color="#58a6ff")
        self.progress.pack(side="bottom", fill="x")
        self.progress.set(0)

        # Status bar
        self.status_text = ctk.CTkLabel(
            self, text="Prêt",
            font=ctk.CTkFont(size=10),
            text_color="#484f58"
        )
        self.status_text.pack(side="bottom", pady=(0, 8))

    def toggle_protection(self):
        if self.protected:
            self.deactivate()
        else:
            self.activate()

    def activate(self):
        self.toggle_btn.configure(state="disabled", text="Connexion en cours...")
        self.status_text.configure(text="Démarrage de Tor...")
        self.progress.start()

        def task():
            try:
                self.tor.start()
                time.sleep(3)
                ip = self.guard.get_current_ip()
                if ip and self.guard.is_ip_french(ip):
                    self.protected = True
                    self.current_ip = ip
                    self.guard.enable_kill_switch()
                    self.guard.block_webrtc()
                    self.after(0, self._on_activated)
                else:
                    self.after(0, self._on_failed, "IP non française obtenue")
            except Exception as e:
                self.after(0, self._on_failed, str(e))

        threading.Thread(target=task, daemon=True).start()

    def deactivate(self):
        self.toggle_btn.configure(state="disabled", text="Déconnexion...")

        def task():
            try:
                self.guard.disable_kill_switch()
                self.tor.stop()
                self.protected = False
                self.after(0, self._on_deactivated)
            except Exception as e:
                self.after(0, self._on_deactivated)

        threading.Thread(target=task, daemon=True).start()

    def change_ip(self):
        if not self.protected: return
        self.change_btn.configure(state="disabled", text="Changement...")
        self.status_text.configure(text="Rotation IP Tor...")
        self.progress.start()

        def task():
            try:
                self.tor.new_identity()
                time.sleep(3)
                ip = self.guard.get_current_ip()
                self.current_ip = ip
                self.after(0, self._on_ip_changed, ip)
            except:
                self.after(0, self._on_ip_changed, self.current_ip)

        threading.Thread(target=task, daemon=True).start()

    def _on_activated(self):
        self.progress.stop()
        self.progress.set(1)
        self.status_indicator.configure(text="●  Protégé", text_color="#3fb950")
        self.ip_display.configure(text=self.current_ip, text_color="#58a6ff")
        self.location_display.configure(text="France (Tor)")
        self.toggle_btn.configure(text="Désactiver la protection", fg_color="#da3633", hover_color="#f85149", state="normal")
        self.change_btn.configure(state="normal")
        self.source_label.configure(text="Source : Tor {fr} ●●○○○")
        self.status_text.configure(text="Protection active — IP masquée")

    def _on_deactivated(self):
        self.progress.stop()
        self.progress.set(0)
        self.status_indicator.configure(text="○  Non protégé", text_color="#f85149")
        self.ip_display.configure(text="Déconnecté", text_color="#c9d1d9")
        self.location_display.configure(text="Votre vraie IP")
        self.toggle_btn.configure(text="Activer la protection", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.change_btn.configure(state="disabled")
        self.source_label.configure(text="Source : Tor + Proxys FR")
        self.status_text.configure(text="Protection désactivée")

    def _on_failed(self, error):
        self.progress.stop()
        self.progress.set(0)
        self.status_indicator.configure(text="✕  Erreur", text_color="#f85149")
        self.ip_display.configure(text="Échec", text_color="#c9d1d9")
        self.location_display.configure(text=str(error)[:60])
        self.toggle_btn.configure(text="Activer la protection", fg_color="#238636", hover_color="#2ea043", state="normal")
        self.status_text.configure(text="Erreur — réessayez")

    def _on_ip_changed(self, ip):
        self.progress.stop()
        self.progress.set(1)
        self.ip_display.configure(text=ip)
        self.change_btn.configure(state="normal", text="Nouvelle IP française")
        self.status_text.configure(text="Nouvelle IP française attribuée")

    def update_loop(self):
        if self.protected:
            try:
                ip = self.guard.get_current_ip()
                if ip and ip != self.current_ip:
                    self.current_ip = ip
                    self.ip_display.configure(text=ip)
            except:
                pass
        self.after(10000, self.update_loop)

if __name__ == "__main__":
    app = FrenchIPMasker()
    app.mainloop()
