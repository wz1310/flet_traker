import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "tracker_config.json")


class AppConfig:
    def __init__(self):
        self.interval_seconds: int = 30
        self.telegram_token: str = ""
        self.telegram_chat_id: str = ""
        self.device_name: str = "HP Saya"
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                self.interval_seconds = data.get("interval_seconds", 30)
                self.telegram_token = data.get("telegram_token", "")
                self.telegram_chat_id = data.get("telegram_chat_id", "")
                self.device_name = data.get("device_name", "HP Saya")
            except Exception:
                pass

    def save(self):
        data = {
            "interval_seconds": self.interval_seconds,
            "telegram_token": self.telegram_token,
            "telegram_chat_id": self.telegram_chat_id,
            "device_name": self.device_name,
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as ex:
            print(f"[Config] Gagal simpan: {ex}")
