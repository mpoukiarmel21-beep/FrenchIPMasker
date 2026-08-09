# Proxy Scraper - Fetch and test free French HTTP/SOCKS5 proxies
import requests
import time
import threading

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
]

class ProxyScraper:
    def __init__(self):
        self.french_proxies = []
        self.working_proxy = None
        self._lock = threading.Lock()

    def fetch_proxies(self):
        """Fetch proxies from multiple sources"""
        proxies = set()
        for url in PROXY_SOURCES:
            try:
                resp = requests.get(url, timeout=10)
                for line in resp.text.split("\n"):
                    line = line.strip()
                    if ":" in line and len(line) < 30:
                        proxies.add(line)
            except:
                pass
        print(f"[Proxy] Fetched {len(proxies)} proxies")
        return list(proxies)

    def test_proxy(self, proxy, timeout=5):
        """Test if a proxy works and is French"""
        try:
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            # Test with ip-api.com
            resp = requests.get("http://ip-api.com/json/?fields=countryCode,ip",
                              proxies=proxies, timeout=timeout)
            data = resp.json()
            if data.get("countryCode") == "FR":
                return True, data.get("ip", proxy)
            return False, None
        except:
            return False, None

    def find_french_proxy(self):
        """Find a working French proxy"""
        proxies = self.fetch_proxies()
        for proxy in proxies:
            ok, ip = self.test_proxy(proxy)
            if ok:
                with self._lock:
                    self.working_proxy = proxy
                    self.french_proxies.append(proxy)
                print(f"[Proxy] Found French proxy: {proxy}")
                return proxy
        return None

    def get_working_french_proxy(self):
        """Get a working French proxy, fetching if needed"""
        if self.working_proxy:
            ok, _ = self.test_proxy(self.working_proxy, timeout=3)
            if ok:
                return self.working_proxy
        return self.find_french_proxy()

    def refresh_async(self):
        """Refresh proxy list in background"""
        t = threading.Thread(target=self.find_french_proxy, daemon=True)
        t.start()
