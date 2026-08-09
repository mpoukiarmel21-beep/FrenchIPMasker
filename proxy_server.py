# Local HTTP Forward Proxy Server
# Routes traffic through French proxies - for ixbrower integration
import socket
import threading
import select
import requests
import sys

class ForwardProxyServer:
    def __init__(self, host="127.0.0.1", port=8080, proxy_manager=None):
        self.host = host
        self.port = port
        self.proxy_manager = proxy_manager
        self.running = False
        self.server_socket = None
        self._thread = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.server_socket.settimeout(1.0)
        self.running = True

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        print(f"[Proxy] Server started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("[Proxy] Server stopped")

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()
            except socket.timeout:
                continue
            except:
                break

    def _handle_client(self, client_sock, addr):
        try:
            request = client_sock.recv(4096)

            if not request:
                client_sock.close()
                return

            # Parse HTTP CONNECT (for HTTPS) or regular HTTP request
            first_line = request.split(b"\r\n")[0].decode("utf-8", errors="ignore")
            parts = first_line.split()

            if len(parts) < 2:
                client_sock.close()
                return

            method = parts[0]
            target = parts[1]

            # Get a working French proxy
            fr_proxy = None
            if self.proxy_manager:
                fr_proxy = self.proxy_manager.get_best()

            if method == "CONNECT":
                # HTTPS tunneling
                self._handle_connect(client_sock, target, fr_proxy)
            else:
                # HTTP forwarding
                self._handle_http(client_sock, request, target, fr_proxy)

        except Exception as e:
            pass
        finally:
            try:
                client_sock.close()
            except:
                pass

    def _handle_connect(self, client_sock, target, fr_proxy):
        """Handle HTTPS CONNECT tunnel via French proxy"""
        try:
            host, port_str = target.split(":")
            port = int(port_str)

            if fr_proxy:
                # Connect through French proxy
                proxy_host, proxy_port = fr_proxy.split(":")
                remote = socket.create_connection((proxy_host, int(proxy_port)), timeout=10)

                # Send CONNECT request to French proxy
                connect_req = f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n"
                remote.send(connect_req.encode())

                # Read response from proxy
                resp = remote.recv(4096)
                if b"200" in resp:
                    client_sock.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

                    # Bidirectional relay
                    self._relay(client_sock, remote)
                else:
                    client_sock.send(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            else:
                # Direct connection (fallback)
                remote = socket.create_connection((host, port), timeout=10)
                client_sock.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                self._relay(client_sock, remote)

        except Exception as e:
            try:
                client_sock.send(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            except:
                pass

    def _handle_http(self, client_sock, request, target, fr_proxy):
        """Forward HTTP request via French proxy"""
        try:
            # Modify request to use absolute URI if needed
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            proxies = None

            if fr_proxy:
                proxies = {"http": f"http://{fr_proxy}", "https": f"http://{fr_proxy}"}

            # Extract method and URL
            first_line = request.split(b"\r\n")[0].decode()
            method = first_line.split()[0]

            if method == "GET":
                url = target if target.startswith("http") else f"http://{target}"
                resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
                client_sock.send(resp.content)
            else:
                # For other methods, do a simple forward
                if target.startswith("http"):
                    resp = requests.request(method, target, headers=headers, proxies=proxies, timeout=15)
                    client_sock.send(resp.content)
                else:
                    client_sock.send(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")

        except Exception as e:
            try:
                client_sock.send(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            except:
                pass

    def _relay(self, sock1, sock2):
        """Bidirectional data relay between two sockets"""
        sockets = [sock1, sock2]
        while self.running:
            try:
                readable, _, _ = select.select(sockets, [], [], 5)
                if not readable:
                    break

                for s in readable:
                    data = s.recv(8192)
                    if not data:
                        return

                    if s == sock1:
                        sock2.send(data)
                    else:
                        sock1.send(data)
            except:
                break

        try:
            sock1.close()
            sock2.close()
        except:
            pass
