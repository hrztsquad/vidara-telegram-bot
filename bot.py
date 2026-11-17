#!/usr/bin/env python3
"""
Telegram Bot for downloading Vidara videos using Pyrogram (MTProto Native).
Supports large file uploads up to 2.000 MB (2 GB) without requiring Docker!
"""

import os
import re
import time
import shutil
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import BotCommand, Message
from pyrogram.errors import FloodWait

from src.vidara.core.engine import VidaraEngine
from src.vidara.utils import sanitize_filename

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/vidara_downloads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "2000"))  # Native MTProto supports 2 GB!

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Regex to detect Vidara URLs
VIDARA_URL_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?vidara\.(?:to|so|cc|org|net)/[^\s]+", re.IGNORECASE)

# Runtime stats
BOT_START_TIME = time.time()
ACTIVE_DOWNLOADS = {}


def get_uptime_str() -> str:
    elapsed = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if days > 0:
        return f"{days} hari, {hours} jam, {minutes} mnt"
    if hours > 0:
        return f"{hours} jam, {minutes} mnt, {seconds} dtk"
    return f"{minutes} mnt, {seconds} dtk"


# Initialize Pyrogram Bot Client
app = Client(
    name="vidara_downloader_bot",
    api_id=int(API_ID) if API_ID and API_ID.isdigit() else 0,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="/tmp"
)


@app.on_message(filters.command(["start"]) & filters.private)
async def start_handler(client: Client, message: Message):
    """Handles /start command."""
    welcome_text = (
        "👋 <b>Halo! Selamat datang di Vidara Downloader Bot (MTProto Edition).</b>\n\n"
        "Bot ini menggunakan teknologi <b>Native MTProto</b> (seperti DOD Downloader) "
        "yang memungkinkan pengiriman file berukuran besar hingga <b>2.000 MB (2 GB)</b> tanpa iklan!\n\n"
        "📋 <b>Menu Perintah:</b>\n"
        "• <code>/download &lt;link&gt;</code> : Mengunduh video dari tautan Vidara.\n"
        "• <code>/status</code> : Melihat kapasitas disk VPS, uptime, & proses aktif.\n"
        "• <code>/help</code> : Panduan bantuan lengkap.\n\n"
        "💡 <i>Tips: Cukup tempelkan (paste) link video Vidara langsung ke chat ini tanpa harus mengetik perintah!</i>"
    )
    await message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


@app.on_message(filters.command(["help"]) & filters.private)
async def help_handler(client: Client, message: Message):
    """Handles /help command."""
    help_text = (
        "📖 <b>Panduan Penggunaan Bot:</b>\n\n"
        "1. <b>Kirim Tautan:</b>\n"
        "   Ketik: <code>/download https://vidara.to/v/xxxx</code>\n"
        "   Atau langsung kirim link: <code>vidara.to/v/xxxx</code>\n\n"
        "2. <b>Cek Status Sistem:</b>\n"
        "   Ketik <code>/status</code> untuk melihat kondisi bot dan sisa ruang penyimpanan VPS.\n\n"
        "3. <b>Progres Transparan:</b>\n"
        "   Pesan akan terus diperbarui secara live memperlihatkan MB yang sedang diunduh ke VPS "
        "   serta persentase (%) saat mengunggah ke chat Telegram Anda."
    )
    await message.reply_text(help_text, parse_mode=ParseMode.HTML)


@app.on_message(filters.command(["status"]) & filters.private)
async def status_handler(client: Client, message: Message):
    """Handles /status command."""
    total, used, free = shutil.disk_usage(DOWNLOAD_DIR)
    total_gb = total / (1024 ** 3)
    used_gb = used / (1024 ** 3)
    free_gb = free / (1024 ** 3)

    active_count = len(ACTIVE_DOWNLOADS)
    if active_count > 0:
        active_list = "\n".join([f"• <i>{info.get('title', 'Video')}</i> ({info.get('progress', '0 MB')})" for info in ACTIVE_DOWNLOADS.values()])
        activity_str = f"⏳ <b>Sedang Berjalan ({active_count} proses):</b>\n{active_list}"
    else:
        activity_str = "💤 <b>Aktivitas:</b> Tidak ada unduhan aktif (Standby)"

    status_message = (
        "🖥️ <b>STATUS SISTEM BOT VIDARA (MTProto)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ <b>Uptime Bot:</b> <code>{get_uptime_str()}</code>\n"
        f"⚙️ <b>Protokol:</b> 🟢 <b>MTProto Native</b> (Max <b>2.000 MB / 2 GB</b>)\n\n"
        f"💾 <b>Penyimpanan VPS:</b>\n"
        f"   • Total   : <code>{total_gb:.1f} GB</code>\n"
        f"   • Terpakai: <code>{used_gb:.1f} GB</code>\n"
        f"   • Sisa    : <code>{free_gb:.1f} GB (Aman)</code>\n\n"
        f"{activity_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <i>Siap menerima dan mengirim video berukuran besar!</i>"
    )
    await message.reply_text(status_message, parse_mode=ParseMode.HTML)


async def process_video_download(client: Client, message: Message, target_url: str):
    """Core logic to download from Vidara and send via Pyrogram MTProto with live progress."""
    chat_id = message.chat.id
    status_msg = await message.reply_text(
        "🔍 <b>[1/3] Menghubungkan ke Vidara & mengambil metadata...</b>",
        parse_mode=ParseMode.HTML
    )
    file_path = None
    title = "Video Vidara"

    ACTIVE_DOWNLOADS[chat_id] = {"title": "Memeriksa URL...", "progress": "0 MB"}

    try:
        loop = asyncio.get_running_loop()
        engine = VidaraEngine(output_dir=DOWNLOAD_DIR)

        # 1. Fetch metadata
        metadata = await loop.run_in_executor(None, lambda: engine.fetch_video_data(target_url))
        title = metadata.title or metadata.filecode or "Vidara Video"
        filename = f"{sanitize_filename(title)}.mp4"
        expected_output_path = os.path.join(DOWNLOAD_DIR, filename)

        ACTIVE_DOWNLOADS[chat_id]["title"] = title

        await status_msg.edit_text(
            f"🎬 <b>{title}</b>\n\n"
            f"⏳ <b>[2/3] Memulai proses download stream via FFmpeg...</b>\n"
            f"📊 Terunduh saat ini: <code>0.0 MB</code>\n"
            f"⚡ Mode: Stream-Copy (Kualitas Asli)",
            parse_mode=ParseMode.HTML
        )

        # 2. Track download progress
        download_finished = asyncio.Event()

        async def track_download_progress():
            last_reported_mb = -1.0
            while not download_finished.is_set():
                await asyncio.sleep(3.5)
                if download_finished.is_set():
                    break
                if os.path.exists(expected_output_path):
                    try:
                        current_mb = os.path.getsize(expected_output_path) / (1024 * 1024)
                        ACTIVE_DOWNLOADS[chat_id]["progress"] = f"{current_mb:.1f} MB"
                        if abs(current_mb - last_reported_mb) >= 1.0:
                            last_reported_mb = current_mb
                            await status_msg.edit_text(
                                f"🎬 <b>{title}</b>\n\n"
                                f"⏳ <b>[2/3] Sedang mengunduh stream video ke VPS...</b>\n"
                                f"📊 Terunduh: <code>{current_mb:.1f} MB</code>\n"
                                f"⚡ Mode: Stream-Copy FFmpeg (Kualitas Asli)",
                                parse_mode=ParseMode.HTML
                            )
                    except Exception:
                        pass

        reporter_task = asyncio.create_task(track_download_progress())

        # 3. Execute download
        try:
            file_path = await loop.run_in_executor(None, lambda: engine.process_download(metadata))
        finally:
            download_finished.set()
            reporter_task.cancel()

        if not file_path or not os.path.exists(file_path):
            raise RuntimeError("File hasil unduhan tidak ditemukan di server VPS.")

        # Check final size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"Downloaded '{title}' ({file_size_mb:.2f} MB)")

        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"⚠️ <b>Ukuran file terlalu besar!</b>\n\n"
                f"Judul: <b>{title}</b>\n"
                f"Ukuran: <code>{file_size_mb:.2f} MB</code>\n\n"
                f"Batas upload Telegram MTProto adalah <b>{MAX_FILE_SIZE_MB} MB (2 GB)</b>.",
                parse_mode=ParseMode.HTML
            )
            return

        # 4. Uploading to Telegram via MTProto with live percentage progress
        await status_msg.edit_text(
            f"🎬 <b>{title}</b>\n\n"
            f"📤 <b>[3/3] Selesai diunduh ({file_size_mb:.1f} MB)!</b>\n"
            f"Sedang mengunggah file video ke chat Telegram Anda...",
            parse_mode=ParseMode.HTML
        )

        last_upload_edit_time = 0

        async def upload_progress_callback(current, total):
            nonlocal last_upload_edit_time
            now = time.time()
            if now - last_upload_edit_time >= 4.0:
                last_upload_edit_time = now
                pct = (current / total) * 100
                current_mb = current / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                try:
                    await status_msg.edit_text(
                        f"🎬 <b>{title}</b>\n\n"
                        f"📤 <b>[3/3] Sedang mengunggah ke Telegram...</b>\n"
                        f"📊 Progres: <code>{pct:.1f}%</code> ({current_mb:.1f} MB / {total_mb:.1f} MB)\n"
                        f"⚡ Jalur: MTProto Native (Max 2.000 MB)",
                        parse_mode=ParseMode.HTML
                    )
                except Exception:
                    pass

        caption = (
            f"🎬 <b>{title}</b>\n"
            f"📦 Ukuran: <code>{file_size_mb:.2f} MB</code>\n"
            f"🔗 <a href='{target_url}'>Tautan Sumber</a>"
        )

        await message.reply_video(
            video=file_path,
            caption=caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
            progress=upload_progress_callback
        )

        # Delete status message on success
        await status_msg.delete()

    except FloodWait as fw:
        logger.warning(f"FloodWait encountered: {fw.value}s")
        await asyncio.sleep(fw.value)
    except Exception as exc:
        logger.error(f"Error handling download for {target_url}: {exc}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Terkendala saat memproses unduhan:</b>\n\n"
            f"Tautan: <code>{target_url}</code>\n"
            f"Alasan: <code>{str(exc)}</code>\n\n"
            f"<i>Silakan periksa kembali apakah video di tautan tersebut masih aktif di Vidara.</i>",
            parse_mode=ParseMode.HTML
        )

    finally:
        ACTIVE_DOWNLOADS.pop(chat_id, None)
        # Cleanup temporary files on VPS to keep disk space clean
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except OSError as cleanup_err:
                logger.warning(f"Failed to delete {file_path}: {cleanup_err}")


@app.on_message(filters.command(["download"]) & filters.private)
async def download_cmd_handler(client: Client, message: Message):
    """Handles /download <url>."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(
            "⚠️ <b>Format perintah salah!</b>\n\n"
            "Gunakan format: <code>/download &lt;link_vidara&gt;</code>\n"
            "<i>Contoh:</i> <code>/download https://vidara.to/v/WJ0DOTFNCx4cg</code>",
            parse_mode=ParseMode.HTML
        )
        return

    raw_url = parts[1].strip()
    match = VIDARA_URL_PATTERN.search(raw_url)
    if not match:
        await message.reply_text(
            "❌ <b>URL tidak valid!</b>\nPastikan tautan berasal dari <code>vidara.to</code> atau <code>vidara.so</code>.",
            parse_mode=ParseMode.HTML
        )
        return

    target_url = match.group(0)
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    await process_video_download(client, message, target_url)


@app.on_message(filters.text & filters.private & ~filters.command(["start", "help", "status", "download"]))
async def direct_url_handler(client: Client, message: Message):
    """Catches direct Vidara URL in text message."""
    text = message.text or ""
    match = VIDARA_URL_PATTERN.search(text)
    if match:
        target_url = match.group(0)
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
        await process_video_download(client, message, target_url)


async def main():
    if not BOT_TOKEN or not API_ID or not API_HASH:
        print("=" * 60)
        print("ERROR: Konfigurasi belum lengkap di .env!")
        print("Pastikan TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, dan TELEGRAM_API_HASH sudah diisi.")
        print("=" * 60)
        return

    print("🚀 Menginisialisasi Pyrogram MTProto Bot Client...")
    await app.start()

    # Register bot menu commands in Telegram UI
    try:
        await app.set_bot_commands([
            BotCommand("download", "Unduh video dari link Vidara"),
            BotCommand("status", "Cek status bot, server, dan penyimpanan VPS"),
            BotCommand("start", "Mulai bot & panduan penggunaan"),
            BotCommand("help", "Bantuan cara penggunaan"),
        ])
        print("✅ Menu perintah bot berhasil didaftarkan di Telegram!")
    except Exception as e:
        logger.warning(f"Gagal mengatur bot commands: {e}")

    me = await app.get_me()
    print(f"🤖 Bot @{me.username} (ID: {me.id}) AKTIF dan SIAP menerima video hingga 2.000 MB (2 GB)!")
    print("⚡ Berjalan melalui protokol MTProto Native (Tanpa Docker).")

    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
