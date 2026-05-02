"""
TrackerService — handles Telegram delivery and location history.
GPS tracking is now natively handled by flet_geolocator in main.py.
"""

import threading
import time
import json
import os
import requests
from datetime import datetime
from typing import Callable, Optional

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "location_history.json")


class TrackerService:
    def __init__(self, config):
        self.config = config
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_location: Optional[dict] = None
        self._callback: Optional[Callable] = None

    def update_location(self, loc: dict):
        """Called by main.py whenever Geolocator receives a new position."""
        self._last_location = loc

    def get_location_once(self) -> Optional[dict]:
        """Get the latest known location."""
        return self._last_location

    def start(self, callback: Callable):
        if self._running:
            return
        self._running = True
        self._callback = callback
        
        # Start a background thread that sends location to Telegram every interval_seconds
        self._thread = threading.Thread(target=self._telegram_loop, daemon=True)
        self._thread.start()
        print("[TrackerService] Tracking dimulai")

    def stop(self):
        self._running = False
        print("[TrackerService] Tracking dihentikan")

    def _telegram_loop(self):
        """Background loop to periodically send the latest location to Telegram."""
        last_sent_timestamp = None

        while self._running:
            loc = self._last_location
            
            # Only send if we have a location and it's newer than the last sent one
            if loc and loc.get("timestamp") != last_sent_timestamp:
                self._save_history(loc)
                sent = self.send_to_telegram(loc)
                if self._callback:
                    self._callback(loc, sent)
                last_sent_timestamp = loc.get("timestamp")
            
            # Sleep in small chunks so stop() is responsive
            for _ in range(max(1, self.config.interval_seconds * 2)):
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
        source_label = "📡 GPS Device"
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
