"""
TrackerService — handles GPS polling and Telegram delivery.

Platform detection:
  - Android (via Flet/Kivy runtime): uses plyer.gps
  - Desktop / fallback: uses ip-api.com for approximate location
    (useful for testing on PC before deploying to Android)
"""

import threading
import time
import json
import os
import requests
from datetime import datetime
from typing import Callable, Optional

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "location_history.json")


def _is_android() -> bool:
    try:
        import android  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        from plyer import gps  # noqa: F401
        import platform
        return platform.system() == "Linux" and "ANDROID_ROOT" in os.environ
    except ImportError:
        pass
    return False


class TrackerService:
    def __init__(self, config):
        self.config = config
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_location: Optional[dict] = None
        self._callback: Optional[Callable] = None
        self._android = _is_android()
        self._gps = None

        if self._android:
            self._init_android_gps()

    # ── Android GPS ────────────────────────────────────────
    def _init_android_gps(self):
        try:
            from plyer import gps
            self._gps = gps
            self._gps.configure(
                on_location=self._on_android_location,
                on_status=self._on_android_status,
            )
            print("[GPS] Android GPS dikonfigurasi")
        except Exception as ex:
            print(f"[GPS] Gagal init Android GPS: {ex}")
            self._android = False

    def _on_android_location(self, **kwargs):
        loc = {
            "lat": kwargs.get("lat", 0.0),
            "lon": kwargs.get("lon", 0.0),
            "accuracy": round(kwargs.get("accuracy", 0), 1),
            "altitude": kwargs.get("altitude", 0.0),
            "speed": kwargs.get("speed", 0.0),
            "timestamp": datetime.now().isoformat(),
        }
        self._last_location = loc
        self._save_history(loc)

        if self._callback:
            sent = self.send_to_telegram(loc)
            self._callback(loc, sent)

    def _on_android_status(self, stype, status):
        print(f"[GPS] Status: {stype} — {status}")

    # ── IP-based fallback (desktop / testing) ─────────────
    def _get_location_by_ip(self) -> Optional[dict]:
        try:
            r = requests.get("http://ip-api.com/json/", timeout=8)
            if r.status_code == 200:
                d = r.json()
                if d.get("status") == "success":
                    return {
                        "lat": d["lat"],
                        "lon": d["lon"],
                        "accuracy": 5000,  # IP-based, low accuracy
                        "altitude": 0.0,
                        "speed": 0.0,
                        "city": d.get("city", ""),
                        "isp": d.get("isp", ""),
                        "timestamp": datetime.now().isoformat(),
                        "source": "ip",
                    }
        except Exception as ex:
            print(f"[GPS] IP fallback gagal: {ex}")
        return None

    # ── Public API ─────────────────────────────────────────
    def get_location_once(self) -> Optional[dict]:
        """Get a single location fix (blocking, max ~10s)."""
        if self._android and self._gps:
            # On Android, last known location from continuous updates
            return self._last_location
        return self._get_location_by_ip()

    def start(self, callback: Callable):
        if self._running:
            return
        self._running = True
        self._callback = callback

        if self._android and self._gps:
            try:
                self._gps.start(minTime=self.config.interval_seconds * 1000, minDistance=0)
                print("[GPS] Android GPS dimulai")
            except Exception as ex:
                print(f"[GPS] Gagal start Android GPS: {ex}")
        else:
            # Desktop polling thread
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
            print("[GPS] Desktop polling dimulai (IP-based)")

    def stop(self):
        self._running = False
        if self._android and self._gps:
            try:
                self._gps.stop()
            except Exception:
                pass
        print("[GPS] Tracking dihentikan")

    def _poll_loop(self):
        """Background polling loop for desktop/IP fallback."""
        while self._running:
            loc = self._get_location_by_ip()
            if loc and self._callback:
                self._save_history(loc)
                sent = self.send_to_telegram(loc)
                self._callback(loc, sent)
            # Sleep in small chunks so stop() is responsive
            for _ in range(self.config.interval_seconds * 2):
                if not self._running:
                    break
                time.sleep(0.5)

    # ── Telegram ───────────────────────────────────────────
    def send_to_telegram(self, loc: dict) -> bool:
        token = self.config.telegram_token.strip()
        chat_id = self.config.telegram_chat_id.strip()
        if not token or not chat_id:
            return False

        maps_url = f"https://maps.google.com/?q={loc['lat']},{loc['lon']}"
        source_label = "📡 GPS" if loc.get("source") != "ip" else "🌐 IP (perkiraan)"
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        text = (
            f"📍 *{self.config.device_name}*\n"
            f"🕐 {ts}\n"
            f"📌 Lat: `{loc['lat']:.6f}`\n"
            f"📌 Lon: `{loc['lon']:.6f}`\n"
            f"🎯 Akurasi: ±{loc.get('accuracy', '?')} m\n"
            f"🔍 Sumber: {source_label}\n"
            f"🗺 [Lihat di Maps]({maps_url})"
        )

        try:
            # Send text message
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                # Also send location pin for easy navigation
                loc_url = f"https://api.telegram.org/bot{token}/sendLocation"
                requests.post(
                    loc_url,
                    json={
                        "chat_id": chat_id,
                        "latitude": loc["lat"],
                        "longitude": loc["lon"],
                    },
                    timeout=10,
                )
                return True
            else:
                print(f"[Telegram] Error {resp.status_code}: {resp.text}")
                return False
        except Exception as ex:
            print(f"[Telegram] Gagal kirim: {ex}")
            return False

    # ── History persistence ────────────────────────────────
    def _save_history(self, loc: dict):
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.insert(0, loc)
        history = history[:500]  # keep last 500 entries

        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as ex:
            print(f"[History] Gagal simpan: {ex}")

    def load_history(self) -> list:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
