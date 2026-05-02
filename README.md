# HP Tracker 📍

Aplikasi pelacak lokasi HP otomatis berbasis Flet Python.
Kirim lokasi ke Telegram secara berkala sebagai perlindungan dari pencurian.

## Fitur
- ✅ Tracking GPS otomatis (interval bisa diatur)
- ✅ Kirim lokasi ke Telegram (teks + pin lokasi)
- ✅ Riwayat lokasi (100 titik terakhir)
- ✅ Buka lokasi langsung di Google Maps
- ✅ Berjalan di background (foreground service Android)
- ✅ Fallback IP-based untuk testing di PC

## Cara Pakai

### 1. Jalankan di PC (testing)
```bash
cd hp_tracker
pip install -r requirements.txt
python main.py
```

### 2. Setup Telegram Bot
1. Chat @BotFather di Telegram → `/newbot`
2. Salin **Bot Token** yang diberikan
3. Chat bot kamu, lalu buka:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Salin **chat_id** dari response
5. Isi di tab **Pengaturan** aplikasi

### 3. Build APK Android
```bash
# Install flet CLI tools
pip install flet

# Build APK (butuh Android SDK / Docker)
flet build apk

# APK ada di: build/apk/
```

## Catatan Penting

### Background Service di Android
Android secara agresif mematikan background apps. Untuk memastikan tracker tetap jalan:
1. Buka **Pengaturan HP** → **Baterai** → **Optimasi Baterai**
2. Cari "HP Tracker" → pilih **Jangan Optimalkan**
3. Aktifkan **Izin Lokasi** → pilih **Izinkan Sepanjang Waktu**

### Izin yang Dibutuhkan
- `ACCESS_FINE_LOCATION` — GPS presisi tinggi
- `ACCESS_BACKGROUND_LOCATION` — lokasi saat app di background
- `FOREGROUND_SERVICE` — service persisten dengan notifikasi
- `INTERNET` — kirim ke Telegram
- `RECEIVE_BOOT_COMPLETED` — auto-start saat HP nyala (opsional)

## Struktur File
```
hp_tracker/
├── main.py              # UI utama (Flet)
├── tracker_service.py   # Logic GPS + Telegram
├── config.py            # Konfigurasi (disimpan lokal)
├── pyproject.toml       # Build config untuk flet build apk
├── requirements.txt
└── README.md
```
