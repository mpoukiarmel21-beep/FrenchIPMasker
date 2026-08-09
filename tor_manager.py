# Tor Manager - Start/stop Tor with French exit nodes
import subprocess
import os
import time
import sys
import zipfile
import urllib.request
import tempfile
import shutil

TOR_VERSION = "14.0.8"
TOR_URL = f"https://archive.torproject.org/tor-package-archive/torbrowser/{TOR_VERSION}/tor-expert-bundle-windows-x86_64-{TOR_VERSION}.tar.gz"
TOR_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FrenchIPMasker", "tor")

class TorManager:
    def __init__(self):
        self.process = None
        self.tor_dir = TOR_DIR
        self.tor_exe = os.path.join(self.tor_dir, "Tor", "tor.exe")
        self.torrc = os.path.join(self.tor_dir, "torrc")
        self._ensure_tor()

    def _ensure_tor(self):
        """Download and extract Tor if not present"""
        if os.path.exists(self.tor_exe):
            return

        os.makedirs(self.tor_dir, exist_ok=True)

        try:
            import requests
            print("[Tor] Downloading Tor Expert Bundle...")
            resp = requests.get(TOR_URL, timeout=120)
            resp.raise_for_status()

            # Save and extract
            tmp = os.path.join(self.tor_dir, "tor.tar.gz")
            with open(tmp, "wb") as f:
                f.write(resp.content)

            import tarfile
            with tarfile.open(tmp) as tf:
                tf.extractall(self.tor_dir)

            os.remove(tmp)
            print("[Tor] Installed successfully")
        except Exception as e:
            print(f"[Tor] Download failed: {e}")

    def _write_torrc(self):
        """Write torrc with French exit nodes"""
        config = """# FrenchIPMasker - French exit nodes only
SOCKSPort 9050
ControlPort 9051
DataDirectory {data_dir}
GeoIPFile {data_dir}\\geoip
GeoIPv6File {data_dir}\\geoip6
# Force French exit nodes
ExitNodes {fr}
StrictNodes 1
# Performance
CircuitBuildTimeout 30
LearnCircuitBuildTimeout 0
# No logs
Log notice stdout
AvoidDiskWrites 1
""".format(data_dir=self.tor_dir.replace("\\", "/"),
           fr="{fr}")

        with open(self.torrc, "w") as f:
            f.write(config)

    def start(self):
        """Start Tor with French exit nodes"""
        if self.process and self.process.poll() is None:
            return

        self._write_torrc()

        self.process = subprocess.Popen(
            [self.tor_exe, "-f", self.torrc],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        print("[Tor] Started (French exit nodes only)")

    def stop(self):
        """Stop Tor"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
            print("[Tor] Stopped")

    def new_identity(self):
        """Request new Tor circuit (new IP)"""
        if not self.process:
            return

        try:
            from stem import Signal
            from stem.control import Controller
            with Controller.from_port(port=9051) as c:
                c.authenticate()
                c.signal(Signal.NEWNYM)
                print("[Tor] New identity requested")
        except ImportError:
            # Fallback: restart Tor
            self.stop()
            time.sleep(2)
            self.start()
            print("[Tor] Restarted for new identity")
        except Exception as e:
            print(f"[Tor] New identity failed: {e}")

    def is_running(self):
        return self.process is not None and self.process.poll() is None
