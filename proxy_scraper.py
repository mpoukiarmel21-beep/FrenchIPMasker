# Infinite Proxy Pool - continuous scraping + instant rotation
import requests
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BUNDLED = [
    "51.158.110.234:3128","51.158.108.215:3128","51.159.30.49:3128",
    "51.158.111.229:3128","51.158.98.123:3128","163.172.176.38:3128",
    "51.158.154.47:3128","51.158.107.202:3128","51.159.6.60:3128",
    "51.158.123.35:3128","163.172.212.35:3128","193.70.114.126:3128",
    "51.158.68.131:3128","51.158.68.24:3128","51.158.100.191:3128",
    "54.38.80.108:3128","51.75.144.249:3128","51.77.149.179:3128",
    "188.165.194.79:3128","193.70.114.125:3128","51.158.119.88:3128",
    "51.159.195.47:3128","51.158.79.48:3128","51.159.196.45:3128",
    "51.158.202.17:3128","51.158.119.212:3128","163.172.132.38:3128",
    "51.158.103.129:3128","51.158.113.130:3128","51.159.14.110:3128",
]

SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=FR&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
]

class InfiniteProxyPool:
    def __init__(self, on_update=None):
        self._all = list(BUNDLED)
        self._ready = []
        self._used = set()
        self._current = None
        self._lock = threading.Lock()
        self._cb = on_update
        self._running = False
        self._workers = 12

    def notify(self, msg, data=None):
        if self._cb:
            try: self._cb(msg, data or {})
            except: pass

    def start(self):
        self._running = True
        self.notify("start", {"total": len(self._all), "ready": 0})

        # Phase 1: test bundled instantly
        self._test_batch(self._all[:25], workers=self._workers)
        if self._ready:
            self._pick()
            self.notify("ready", self._status())
            # Phase 2+3 in background
            threading.Thread(target=self._background, daemon=True).start()
            return True

        # Phase 2: scrape web
        self.notify("scraping", {"total": 0, "ready": 0})
        self._scrape()
        self._test_batch(self._all[:40], workers=self._workers)
        if self._ready:
            self._pick()
            self.notify("ready", self._status())
            threading.Thread(target=self._background, daemon=True).start()
            return True

        self.notify("noproxy", {})
        return False

    def stop(self):
        self._running = False

    def rotate(self):
        """Instant rotation to next pre-tested proxy"""
        if self._ready:
            self._pick()
            self.notify("rotated", self._status())
            return self._current
        return None

    def _pick(self):
        if len(self._ready) == 0: return
        # Pick next available, avoid repeats
        available = [p for p in self._ready if p["proxy"] not in self._used]
        if not available:
            self._used.clear()
            available = self._ready
        self._current = random.choice(available)
        self._used.add(self._current["proxy"])

    def _test_one(self, proxy):
        try:
            r = requests.get("http://ip-api.com/json/?fields=countryCode,ip",
                proxies={"http": f"http://{proxy}"}, timeout=3)
            if r.json().get("countryCode") == "FR":
                return {"proxy": proxy, "ip": r.json().get("ip", proxy), "latency": int(r.elapsed.total_seconds()*1000)}
        except:
            pass
        return None

    def _test_batch(self, proxies, workers=10):
        tested = 0
        found = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(self._test_one, p): p for p in proxies if p not in [x["proxy"] for x in self._ready]}
            for f in as_completed(futs):
                tested += 1
                if not self._running: break
                r = f.result()
                if r:
                    self._ready.append(r)
                    found += 1
                    self.notify("found", {"tested": tested, "total": len(proxies), "ready": len(self._ready), "ip": r["ip"]})
                elif tested % 10 == 0:
                    self.notify("testing", {"tested": tested, "total": len(proxies), "ready": len(self._ready)})

    def _scrape(self):
        new = set()
        for url in SOURCES:
            if not self._running: break
            try:
                r = requests.get(url, timeout=8)
                for line in r.text.splitlines():
                    line = line.strip()
                    if ":" in line and 5 < len(line) < 25 and not line.startswith("#"):
                        new.add(line)
            except: pass
        with self._lock:
            for p in new:
                if p not in self._all:
                    self._all.append(p)
            self.notify("scraped", {"total": len(self._all), "ready": len(self._ready)})

    def _background(self):
        """Continuous: scrape -> test -> repeat"""
        cycle = 0
        while self._running:
            cycle += 1
            time.sleep(15)
            if not self._running: break
            self._scrape()
            unprocessed = [p for p in self._all if p not in [x["proxy"] for x in self._ready]]
            if unprocessed:
                self._test_batch(unprocessed[:30], workers=10)
            self.notify("refresh", self._status())

    def _status(self):
        return {
            "total": len(self._all), "ready": len(self._ready),
            "ip": self._current["ip"] if self._current else "...",
            "proxy": self._current["proxy"] if self._current else None,
            "latency": self._current.get("latency", 0) if self._current else 0
        }

    def get_status(self): return self._status()
    def get_current_ip(self): return self._current["ip"] if self._current else "..."
