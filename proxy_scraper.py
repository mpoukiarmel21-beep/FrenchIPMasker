# Fast Proxy Manager - Pre-loaded French proxies + parallel testing + real-time UI
import requests
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Pre-loaded French proxies (updated regularly, instant startup)
BUNDLED_PROXIES = [
    "51.158.110.234:3128", "51.158.108.215:3128", "51.159.30.49:3128",
    "51.158.111.229:3128", "51.158.98.123:3128", "163.172.176.38:3128",
    "51.158.154.47:3128", "51.158.107.202:3128", "51.159.6.60:3128",
    "51.158.123.35:3128", "163.172.212.35:3128", "193.70.114.126:3128",
    "51.158.68.131:3128", "51.158.68.24:3128", "51.158.100.191:3128",
    "54.38.80.108:3128", "51.75.144.249:3128", "51.77.149.179:3128",
    "188.165.194.79:3128", "193.70.114.125:3128"
]

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=FR&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

class FastProxyManager:
    def __init__(self, on_update=None):
        self.proxies = list(BUNDLED_PROXIES)
        self.working = []
        self.current = None
        self._lock = threading.Lock()
        self._on_update = on_update
        self._stop = False

    def set_callback(self, cb):
        self._on_update = cb

    def notify(self, msg, data=None):
        if self._on_update:
            self._on_update(msg, data)

    def test_one(self, proxy, timeout=3):
        try:
            url = "http://ip-api.com/json/?fields=countryCode,ip,query"
            resp = requests.get(url, proxies={"http": f"http://{proxy}"}, timeout=timeout)
            data = resp.json()
            if data.get("countryCode") == "FR":
                return {"proxy": proxy, "ip": data.get("ip", proxy)}
        except:
            pass
        return None

    def test_batch(self, proxies, max_workers=10):
        results = []
        total = len(proxies)
        done = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.test_one, p, 3): p for p in proxies}
            for f in as_completed(futures):
                done += 1
                if self._stop: break
                if done % 5 == 0:
                    self.notify("Testing...", {"done": done, "total": total, "found": len(results)})
                r = f.result()
                if r:
                    results.append(r)
                    self.notify("Found FR proxy!", {"done": done, "total": total, "found": len(results), "ip": r["ip"]})

        with self._lock:
            self.working = results
        return results

    def start(self):
        self._stop = False
        self.notify("Fetching...", {"done": 0, "total": 0, "found": 0})

        # Step 1: Test bundled proxies first (fast, < 3 seconds)
        self.notify("Testing pre-loaded...", {"done": 0, "total": len(self.proxies), "found": 0})
        working = self.test_batch(self.proxies[:20], max_workers=15)

        if working:
            self.current = random.choice(working)
            self.notify("Ready!", {"done": len(self.proxies), "total": len(self.proxies), "found": len(working), "ready": True})
            # Continue scraping in background
            threading.Thread(target=self._scrape_background, daemon=True).start()
            return working

        # Step 2: Scrape from web sources
        self.notify("Scraping web...", {"done": 0, "total": 0, "found": 0})
        self._scrape_online()
        working = self.test_batch(self.proxies[:30], max_workers=15)

        if working:
            self.current = random.choice(working)
        self.notify("Ready!" if working else "No proxies found", {
            "done": len(self.proxies), "total": len(self.proxies),
            "found": len(working), "ready": bool(working)
        })
        return working

    def _scrape_online(self):
        new = set()
        for url in PROXY_SOURCES:
            try:
                resp = requests.get(url, timeout=8)
                for line in resp.text.splitlines():
                    line = line.strip()
                    if ":" in line and len(line) < 25:
                        new.add(line)
            except:
                pass
        with self._lock:
            for p in new:
                if p not in self.proxies:
                    self.proxies.append(p)

    def _scrape_background(self):
        self._scrape_online()
        if not self._stop:
            self.test_batch(self.proxies[20:50], max_workers=10)

    def rotate(self):
        if self.working:
            self.current = random.choice(self.working)
            return self.current
        return None

    def get_current_ip(self):
        if self.current:
            return self.current.get("ip", "...")
        return "..."

    def get_status(self):
        with self._lock:
            return {"total": len(self.proxies), "working": len(self.working),
                    "current_ip": self.get_current_ip(),
                    "current_proxy": self.current["proxy"] if self.current else None}

    def stop(self):
        self._stop = True
