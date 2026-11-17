#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  Deploying Vidara Telegram Downloader    "
echo "=========================================="

# 1. Pastikan dependencies sistem terpasang
echo "[1/5] Memeriksa & menginstal FFmpeg, Python, dan Git..."
if [ -x "$(command -v apt)" ]; then
    sudo apt update && sudo apt install -y ffmpeg python3 python3-pip python3-venv git
elif [ -x "$(command -v dnf)" ]; then
    sudo dnf install -y ffmpeg python3 python3-pip git
fi

# 2. Setup Virtual Environment
echo "[2/5] Menyiapkan virtual environment Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Setup .env file jika belum ada
echo "[3/5] Memeriksa konfigurasi .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "PENTING: File .env telah dibuat dari .env.example."
    echo "Silakan edit file .env dan isi TELEGRAM_BOT_TOKEN Anda!"
fi

# 4. Setup Systemd Service
echo "[4/5] Menyiapkan systemd service..."
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

cat <<EOF | sudo tee /etc/systemd/system/vidarabot.service > /dev/null
[Unit]
Description=Telegram Vidara Downloader Service
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python ${CURRENT_DIR}/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vidarabot
sudo systemctl restart vidarabot

echo "=========================================="
echo "✅ Deployment Selesai!"
echo "Bot sudah aktif di background 24/7."
echo ""
echo "Perintah berguna:"
echo "• Cek status bot : sudo systemctl status vidarabot"
echo "• Lihat logs live: sudo journalctl -u vidarabot -f"
echo "• Restart bot    : sudo systemctl restart vidarabot"
echo "• Stop bot       : sudo systemctl stop vidarabot"
echo "=========================================="
