# Shared Proxy Manager - Fetch, test, and rotate free French proxies
import requests
import threading
import time
import random

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=FR&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=FR&ssl=all&anonymity=all",
]

GEO_CHECK_URL = "http://ip-api.com/json/{ip}?fields=countryCode,country,city,isp"
IP_CHECK_URL = "http://ip-api.com/json/?fields=countryCode,ip"

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.working_proxies = []
        self.current_proxy = None
        self._lock = threading.Lock()
        self._refresh_thread = None

    def fetch_all(self):
        """Fetch proxies from all sources"""
        all_proxies = set()
        for url in PROXY_SOURCES:
            try:
                resp = requests.get(url, timeout=15)
                for line in resp.text.splitlines():
                    line = line.strip()
                    if ":" in line and len(line) < 30 and not line.startswith("#"):
                        all_proxies.add(line)
            except:
                pass

        with self._lock:
            self.proxies = list(all_proxies)

        print(f"[Proxy] Fetched {len(self.proxies)} proxies")
        return self.proxies

    def test_one(self, proxy, timeout=6):
        """Test if a proxy works and check its country"""
        try:
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            resp = requests.get(IP_CHECK_URL, proxies=proxies, timeout=timeout)
            data = resp.json()
            country = data.get("countryCode", "")
            ip = data.get("ip", proxy)
            return country == "FR", ip, country
        except:
            return False, proxy, "?"

    def test_french(self, max_test=80):
        """Test proxies and collect working French ones"""
        working = []
        proxies = self.proxies[:max_test] if len(self.proxies) > max_test else self.proxies

        for proxy in proxies:
            ok, ip, country = self.test_one(proxy, timeout=5)
            if ok:
                working.append({"proxy": proxy, "ip": ip, "country": country})
                print(f"[Proxy] FR: {proxy} -> {ip}")

        with self._lock:
            self.working_proxies = working

        print(f"[Proxy] Found {len(working)} French proxies")
        return working

    def get_best(self):
        """Get the best working French proxy"""
        if self.working_proxies:
            p = random.choice(self.working_proxies)
            ok, _, _ = self.test_one(p["proxy"], timeout=3)
            if ok:
                with self._lock:
                    self.current_proxy = p
                return p["proxy"]

        # Try to find one
        for _ in range(5):
            if self.proxies:
                proxy = random.choice(self.proxies)
                ok, ip, country = self.test_one(proxy, timeout=4)
                if ok:
                    p = {"proxy": proxy, "ip": ip, "country": country}
                    with self._lock:
                        self.working_proxies.append(p)
                        self.current_proxy = p
                    return proxy

        return None

    def refresh_background(self):
        """Refresh proxy list in background thread"""
        def task():
            self.fetch_all()
            self.test_french(max_test=50)

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def get_current_ip(self):
        """Get the IP of the current proxy"""
        if self.current_proxy:
            return self.current_proxy.get("ip", "...")
        return "..."

    def get_status(self):
        """Get current status info"""
        return {
            "total": len(self.proxies),
            "working_french": len(self.working_proxies),
            "current_ip": self.get_current_ip(),
            "current_proxy": self.current_proxy["proxy"] if self.current_proxy else None
        }
