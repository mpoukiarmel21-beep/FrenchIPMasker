#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
French Proxy Tool - find + serve live French proxies (tested for real).
Usage:
  python french_proxy_tool.py list   [--count N] [--out proxies_fr.txt]
  python french_proxy_tool.py serve  [--port 8080] [--count 15]

list  : scrape + test every proxy FOR REAL (exit IP checked via ip-api.com
        THROUGH the proxy) and keep only proxies whose exit IP is in France.
        Saves them to the output file (one ip:port per line).
serve : local HTTP proxy on 127.0.0.1:PORT. Every new connection is routed
        through a DIFFERENT live French proxy (automatic rotation, fresh IP).
        In IXBrowser: profile -> proxy -> type HTTP -> 127.0.0.1:PORT
"""
import argparse
import json
import random
import re
import select
import socket
import sys
import threading
import time
import urllib.request

SOURCES_FR = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=FR&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=3000&country=FR&ssl=all&anonymity=all",
]
SOURCES_GLOBAL = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
]
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}:\d{2,5}$")


def parse_proxy(line):
    """Accept ip:port, http://ip:port, https://ip:port, socks5://ip:port.
    Returns (ip:port, kind) where kind in {'http','socks'}."""
    line = line.strip()
    kind = "http"
    for prefix in ("http://", "https://", "socks5://", "socks4://", "socks://"):
        if line.startswith(prefix):
            kind = "http" if prefix in ("http://", "https://") else "socks"
            line = line[len(prefix):]
            break
    if IP_RE.match(line):
        return line, kind
    return None, None


def fetch_text(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def scrape():
    fr, glob_ = set(), set()

    def work(url, target):
        try:
            for line in fetch_text(url).splitlines():
                p, _k = parse_proxy(line)
                if p:
                    target.add((p, _k))
        except Exception:
            pass

    threads = [threading.Thread(target=work, args=(u, fr)) for u in SOURCES_FR]
    threads += [threading.Thread(target=work, args=(u, glob_)) for u in SOURCES_GLOBAL]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return list(fr), list(glob_)


def test_proxy(p, timeout=3):
    """Real test: the request goes THROUGH the proxy, ip-api returns the proxy's
    own exit IP + country. ipwho.is is used as fallback. Keep only FR exits."""
    try:
        ph = urllib.request.ProxyHandler({"http": "http://" + p, "https": "http://" + p})
        op = urllib.request.build_opener(ph)
        r = op.open("http://ip-api.com/json/?fields=status,countryCode,query", timeout=timeout)
        d = json.loads(r.read().decode("utf-8", "ignore"))
        if d.get("status") == "success" and d.get("countryCode") == "FR" and d.get("query"):
            return d["query"]
    except Exception:
        pass
    try:
        ph = urllib.request.ProxyHandler({"http": "http://" + p, "https": "http://" + p})
        op = urllib.request.build_opener(ph)
        r = op.open("http://ipwho.is/", timeout=timeout)
        d = json.loads(r.read().decode("utf-8", "ignore"))
        if d.get("success") and d.get("country_code") == "FR" and d.get("ip"):
            return d["ip"]
    except Exception:
        pass
    return None


def find_fr(count=10, workers=20, out=None, verbose=True, only_http=False):
    fr, glob_ = scrape()
    if only_http:
        fr = [x for x in fr if x[1] == "http"]
        glob_ = [x for x in glob_ if x[1] == "http"]
    if verbose:
        print("[scrape] FR-specific: %d  global: %d" % (len(fr), len(glob_)))
    candidates = [x[0] for x in fr] + [x[0] for x in glob_]
    random.shuffle(candidates)
    candidates = candidates[:800]

    results = []
    used_ip = set()
    lock = threading.Lock()
    idx = [0]

    def worker():
        while True:
            with lock:
                if len(results) >= count or idx[0] >= len(candidates):
                    return
                i = idx[0]
                idx[0] += 1
            p = candidates[i]
            ip = test_proxy(p)
            if ip:
                with lock:
                    if ip not in used_ip and len(results) < count:
                        used_ip.add(ip)
                        results.append((p, ip))
                        if verbose:
                            print("[+] %-21s -> %s (FR)   [%d/%d]" % (p, ip, len(results), count))

    ts = [threading.Thread(target=worker) for _ in range(min(workers, max(1, len(candidates))))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    if verbose:
        print("[done] %d live FR proxy(s)" % len(results))
    if out and results:
        with open(out, "w") as f:
            for p, _ip in results:
                f.write(p + "\n")
        if verbose:
            print("[saved] %s" % out)
    return results


# ------------------------- serve mode -------------------------

class Rotator:
    def __init__(self, min_pool=5, count=15):
        self.min_pool = min_pool
        self.count = count
        self.queue = []
        self.lock = threading.Lock()
        self.refreshing = False
        self.last_err = ""

    def refill(self):
        with self.lock:
            if self.refreshing:
                return
            self.refreshing = True
        try:
            found = find_fr(count=self.count, verbose=False, only_http=True)
            with self.lock:
                existing = set(self.queue)
                fresh = [p for p, _ip in found if p not in existing]
                self.queue = fresh + self.queue
                print("[pool] refilled: +%d (total %d)" % (len(fresh), len(self.queue)))
        finally:
            with self.lock:
                self.refreshing = False

    def next(self):
        """Pop the least-recently-used live proxy (round robin, no immediate reuse)."""
        with self.lock:
            if not self.queue and not self.refreshing:
                print("[pool] empty, refilling...")
            if not self.queue:
                return None
            p = self.queue.pop(0)
            self.queue.append(p)  # recycle at the end -> fresh per connection
            return p


def pump(src, dst, timeout=30):
    try:
        while True:
            r, _, _ = select.select([src, dst], [], [], timeout)
            if not r:
                return
            for s in r:
                data = s.recv(65536)
                if not data:
                    return
                other = dst if s is src else src
                other.sendall(data)
    except Exception:
        pass


def handle(client, rot):
    try:
        client.settimeout(20)
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = client.recv(4096)
            if not chunk:
                return
            head += chunk
            if len(head) > 65536:
                return
        first = head.split(b"\r\n", 1)[0].decode("latin-1", "ignore")
        parts = first.split(" ")
        if len(parts) < 2:
            return
        method, target = parts[0], parts[1]

        upstream = rot.next()
        if not upstream:
            client.sendall(b"HTTP/1.1 502 No proxy available\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            return

        host, port = upstream.rsplit(":", 1)
        try:
            u = socket.create_connection((host, int(port)), timeout=10)
        except Exception:
            print("[-] dead upstream %s" % upstream)
            return

        if method.upper() == "CONNECT":
            addr = target
            u.sendall(b"CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (addr.encode(), addr.encode()))
            resp = b""
            while b"\r\n\r\n" not in resp:
                chunk = u.recv(4096)
                if not chunk:
                    break
                resp += chunk
            if resp.split(b" ", 2)[1:2] and resp.split(b" ", 2)[1].startswith(b"2"):
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                pump(client, u)
            u.close()
        else:
            u.sendall(head)
            client.sendall(b"")
            pump(client, u)
            u.close()
    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass


def serve(port=8080, count=15, min_pool=5):
    rot = Rotator(min_pool=min_pool, count=count)
    print("[pool] first refill (this can take ~30s)...")
    rot.refill()

    if not rot.queue:
        print("[!] no French proxy found yet. Retrying in background every 20s.")
        threading.Thread(target=lambda: _bg_refill(rot), daemon=True).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(64)
    print("[serve] listening on 127.0.0.1:%d" % port)
    print("[serve] IXBrowser profile -> proxy -> type HTTP -> 127.0.0.1:%d" % port)
    print("[serve] Ctrl+C to stop")
    while True:
        try:
            c, _ = srv.accept()
            threading.Thread(target=handle, args=(c, rot), daemon=True).start()
        except KeyboardInterrupt:
            break


def _bg_refill(rot):
    while True:
        time.sleep(20)
        rot.refill()


def main():
    ap = argparse.ArgumentParser(description="Find live French proxies, or serve them locally.")
    ap.add_argument("mode", nargs="?", default="list", choices=["list", "serve"])
    ap.add_argument("--count", type=int, default=10, help="number of French proxies to find")
    ap.add_argument("--out", default="proxies_fr.txt", help="output file for list mode")
    ap.add_argument("--port", type=int, default=8080, help="local port for serve mode")
    ap.add_argument("--min-pool", type=int, default=5, help="min pool before refill in serve mode")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    if args.mode == "serve":
        serve(port=args.port, count=args.count, min_pool=args.min_pool)
    else:
        find_fr(count=args.count, out=args.out)


if __name__ == "__main__":
    main()
