# Network Guard - IP detection, DNS leak prevention, WebRTC blocking, kill switch
import requests
import subprocess
import sys
import os
import json
import ctypes

class NetworkGuard:
    def __init__(self):
        self.kill_switch_active = False

    def get_current_ip(self, use_tor=True):
        """Get current public IP, optionally via Tor"""
        proxies = None
        if use_tor:
            proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}

        services = [
            ("https://api.ipify.org?format=json", proxies),
            ("http://ip-api.com/json/", None),
            ("https://httpbin.org/ip", proxies),
        ]

        for url, prx in services:
            try:
                resp = requests.get(url, proxies=prx, timeout=8)
                data = resp.json()
                ip = data.get("ip", "")
                if ip:
                    return ip
            except:
                continue

        return None

    def get_ip_info(self, ip):
        """Get geolocation info for an IP"""
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=country,countryCode,city,isp", timeout=5)
            return resp.json()
        except:
            return {}

    def is_ip_french(self, ip):
        """Check if an IP is French"""
        info = self.get_ip_info(ip)
        return info.get("countryCode") == "FR"

    def set_system_proxy(self, enable=True):
        """Set Windows system proxy to route through Tor"""
        if sys.platform != "win32":
            return

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_SET_VALUE)

            if enable:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "socks=127.0.0.1:9050")
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
            else:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)

            winreg.CloseKey(key)

            # Notify system of change
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        except Exception as e:
            print(f"[Network] Proxy config failed: {e}")

    def enable_kill_switch(self):
        """Enable system proxy routing through Tor"""
        self.kill_switch_active = True
        self.set_system_proxy(True)

    def disable_kill_switch(self):
        """Disable system proxy routing"""
        self.kill_switch_active = False
        self.set_system_proxy(False)

    def block_webrtc(self):
        """Block WebRTC leaks via Windows firewall rule"""
        if sys.platform != "win32":
            return

        try:
            rule_name = "FrenchIPMasker_WebRTC_Block"
            # Check if rule already exists
            result = subprocess.run(
                f'netsh advfirewall firewall show rule name="{rule_name}"',
                shell=True, capture_output=True, text=True
            )
            if "No rules match" in result.stdout:
                # Block common WebRTC ports
                for port in ["3478", "19302", "19305", "19307", "19308", "19309"]:
                    subprocess.run(
                        f'netsh advfirewall firewall add rule name="{rule_name}_{port}" '
                        f'dir=out protocol=UDP localport={port} action=block',
                        shell=True, capture_output=True
                    )
                print("[Network] WebRTC ports blocked")
        except Exception as e:
            print(f"[Network] WebRTC block failed: {e}")

    def unblock_webrtc(self):
        """Remove WebRTC firewall rules"""
        if sys.platform != "win32":
            return

        try:
            subprocess.run(
                'netsh advfirewall firewall delete rule name="FrenchIPMasker_WebRTC_Block_*"',
                shell=True, capture_output=True
            )
        except:
            pass

    def check_dns_leak(self):
        """Check for DNS leaks"""
        try:
            resp = requests.get("https://dnsleaktest.com/json", timeout=8)
            data = resp.json()
            servers = data.get("dns", [])
            for srv in servers:
                if srv.get("country_code") != "FR":
                    return False, srv
            return True, None
        except:
            return True, None

    def force_french_timezone(self):
        """Set system timezone to Europe/Paris"""
        if sys.platform != "win32":
            return

        try:
            subprocess.run(
                'tzutil /s "Romance Standard Time"',
                shell=True, capture_output=True
            )
        except:
            pass

    def restore_timezone(self):
        """Restore original timezone"""
        # Windows doesn't have easy way to restore previous TZ
        pass
