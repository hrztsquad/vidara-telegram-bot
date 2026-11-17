# 🎬 Vidara Downloader Telegram Bot

Telegram Bot bertenaga tinggi untuk mengekstrak dan mengunduh video streaming HLS langsung dari **Vidara** (`vidara.to` / `vidara.so`) tanpa iklan, lalu mengirimkannya langsung ke obrolan Telegram pengguna.

Proyek ini mengintegrasikan mesin ekstraksi dari [VidaraCLI](https://github.com/RozhakDev/VidaraCLI) dengan `python-telegram-bot` dan FFmpeg.

---

## ✨ Fitur Utama

- **Bebas Iklan (*Ad-Free*)**: Mem-bypass pemutar web dan pop-up iklan dengan langsung mengambil stream HLS (`.m3u8`) dari API internal.
- **Dua Cara Penggunaan**:
  - Gunakan perintah: `/download https://vidara.to/e/...`
  - Atau cukup **kirimkan link video langsung** ke obrolan bot.
- **Kualitas Asli & Cepat**: Menggunakan proses *stream copy* FFmpeg (`-c copy`), sehingga proses pengunduhan sangat cepat dan tanpa beban CPU berlebih.
- **Pembersihan Otomatis (*Auto-Cleanup*)**: File video sementara di VPS otomatis dihapus setelah terkirim ke Telegram agar tidak menghabiskan ruang penyimpanan (*storage*).
- **Siap Jalan 24/7 di VPS**: Disertai konfigurasi `systemd` dan skrip `deploy.sh` otomatis agar bot tetap aktif tanpa henti meskipun sesi SSH ditutup.

---

## 📋 Prasyarat Sistem

- **VPS Linux** (Ubuntu / Debian / CentOS / dsb.)
- **Python 3.8+**
- **FFmpeg** terpasang di sistem
- **Token Bot Telegram** dari [@BotFather](https://t.me/BotFather)

---

## 🚀 Panduan Instalasi Cepat di VPS (Otomatis)

1. **Clone repositori ini ke VPS Anda:**
   ```bash
   git clone https://github.com/hrztsquad/vidara-telegram-bot.git
   cd vidara-telegram-bot
   ```

2. **Buat file `.env` dan masukkan Token Bot Telegram Anda:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Isi bagian `TELEGRAM_BOT_TOKEN`:
   ```env
   TELEGRAM_BOT_TOKEN="9135755025:AAFd1XO9HJ9yp_2W7A7KSQKBFmzzVCNKqJE"
   ```
   *(Simpan dengan menekan `Ctrl + O`, `Enter`, lalu `Ctrl + X`)*.

3. **Jalankan skrip deployment otomatis:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

Skrip di atas akan secara otomatis menginstal FFmpeg, membuat virtual environment, memasang dependensi, mendaftarkan `systemd service`, dan langsung menyalakan bot di latar belakang (*background*).

---

## 🛠️ Instalasi Manual (Langkah demi Langkah)

Jika Anda ingin menjalankannya secara manual tanpa skrip:

```bash
# 1. Update sistem dan instal paket yang dibutuhkan
sudo apt update && sudo apt install -y ffmpeg python3 python3-pip python3-venv git

# 2. Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Instal dependensi Python
pip install -r requirements.txt

# 4. Salin dan edit konfigurasi .env
cp .env.example .env
nano .env

# 5. Jalankan bot untuk pengetesan
python bot.py
```

---

## 🔄 Mengelola Bot di VPS (Systemd)

Setelah `systemd` aktif, Anda dapat mengontrol bot kapan saja dengan perintah:

| Aksi | Perintah Terminal |
| :--- | :--- |
| **Cek Status Bot** | `sudo systemctl status vidarabot` |
| **Melihat Log Real-time** | `sudo journalctl -u vidarabot -f` |
| **Restart Bot** | `sudo systemctl restart vidarabot` |
| **Menghentikan Bot** | `sudo systemctl stop vidarabot` |
| **Menyalakan Bot** | `sudo systemctl start vidarabot` |

---

## ⚠️ Catatan Batasan Ukuran File Telegram

Server Telegram Bot standar membatasi unggahan file video maksimal **50 MB** per file. 
- Jika file melebihi 50 MB, bot akan menampilkan pesan pemberitahuan.
- Untuk mengunggah file hingga **2 GB (2000 MB)**, Anda dapat mengaktifkan *Local Telegram Bot API Server* di VPS Anda.

---

## 📄 Lisensi & Disclaimer

Proyek ini disediakan untuk tujuan edukasi dan pengarsipan pribadi (*personal archiving*). Pengguna bertanggung jawab penuh atas konten yang diunduh sesuai dengan ketentuan layanan masing-masing platform.

Lisensi di bawah **MIT License**.
