# 🎬 Vidara Downloader Telegram Bot (MTProto Edition)

Telegram Bot bertenaga tinggi untuk mengekstrak dan mengunduh video streaming HLS langsung dari **Vidara** (`vidara.to` / `vidara.so`) tanpa iklan, lalu mengirimkannya langsung ke chat Telegram pengguna hingga ukuran **2.000 MB (2 GB)**!

Bot ini menggunakan protokol **Native MTProto (Pyrogram)** — teknologi yang sama seperti bot terkenal (*DOD Downloader*) — sehingga **TIDAK MEMERLUKAN DOCKER ATAU SERVER PERANTARA LAINNYA**.

---

## ✨ Fitur Utama

- **Native MTProto (Batas Upload 2 GB)**: Tidak terhalang batas 50 MB bawaan HTTP Telegram, mampu mengirim video 69 MB, 400 MB, hingga 2 GB.
- **Tanpa Docker**: Murni berjalan melalui Python di VPS tanpa perlu port 8081 atau container Docker.
- **Progres Live 2 Arah**:
  - Saat Download: Memperlihatkan akumulasi MB terunduh ke VPS secara real-time.
  - Saat Upload: Menampilkan persentase (`%`) dan MB yang sedang diunggah ke chat Telegram.
- **Menu Tombol Resmi Telegram**: Tombol menu praktis di kiri bawah layar obrolan.
- **Perintah `/status` Sistem**: Cek uptime bot, sisa kapasitas storage VPS (100 GB), dan status proses aktif.
- **Pembersihan Otomatis (*Auto-Cleanup*)**: File sementara di VPS otomatis dihapus setelah terkirim agar storage tetap bersih.
- **Aktif 24/7 di Background**: Berjalan via `systemd service` Linux.

---

## 📋 Prasyarat

- **VPS Linux** (Ubuntu / Debian)
- **Python 3.8+** & **FFmpeg**
- **Token Bot** dari [@BotFather](https://t.me/BotFather)
- **API ID & API Hash** dari [my.telegram.org](https://my.telegram.org)

---

## 🚀 Panduan Instalasi & Jalankan di VPS

Jalankan perintah ini di terminal VPS Anda:

```bash
# 1. Masuk ke folder bot dan tarik kode terbaru
cd ~/vidara-telegram-bot
git pull

# 2. Aktifkan virtual environment dan pasang pustaka Pyrogram
source venv/bin/activate
pip install -r requirements.txt

# 3. Pastikan konfigurasi .env sudah lengkap
nano .env
```

Pastikan isi `.env` Anda seperti ini:
```env
TELEGRAM_BOT_TOKEN="9135755025:AAFd1XO9HJ9yp_2W7A7KSQKBFmzzVCNKqJE"
TELEGRAM_API_ID="33293249"
TELEGRAM_API_HASH="a37a1817bb119b4e09ec45728794d622"
DOWNLOAD_DIR="/tmp/vidara_downloads"
```
*(Simpan dengan `Ctrl + O`, `Enter`, lalu `Ctrl + X`)*.

```bash
# 4. Restart bot Anda
sudo systemctl restart vidarabot
sudo systemctl status vidarabot --no-pager
```

---

## 🎮 Penggunaan di Telegram

1. Buka obrolan dengan bot: **[@vidaradownload_bot](https://t.me/vidaradownload_bot)**
2. Kirim perintah:
   - `/start` : Memulai bot & melihat panduan.
   - `/status` : Melihat kapasitas sisa disk VPS dan proses aktif.
   - `/download https://vidara.to/v/xxxx` : Mengunduh video.
   - Atau langsung **kirim/paste link video** ke chat bot!
