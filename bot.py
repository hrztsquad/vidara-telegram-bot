#!/usr/bin/env python3
"""
Telegram Bot for downloading Vidara videos.
Seamlessly integrates VidaraEngine with python-telegram-bot.
Equipped with live progress tracking, /status command, and Telegram command menu.
"""

import os
import re
import time
import shutil
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Load environment variables
load_dotenv()

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
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/vidara_downloads")
LOCAL_BOT_API_URL = os.getenv("LOCAL_BOT_API_URL", "").strip()
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "2000" if LOCAL_BOT_API_URL else "50"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Regex to detect Vidara URLs (with or without https/http)
VIDARA_URL_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?vidara\.(?:to|so|cc|org|net)/[^\s]+", re.IGNORECASE)

# Runtime statistics
BOT_START_TIME = time.time()
ACTIVE_DOWNLOADS = {}  # chat_id -> dict of info


def get_uptime_str() -> str:
    """Returns human-readable uptime."""
    elapsed = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if days > 0:
        return f"{days} hari, {hours} jam, {minutes} mnt"
    if hours > 0:
        return f"{hours} jam, {minutes} mnt, {seconds} dtk"
    return f"{minutes} mnt, {seconds} dtk"


async def set_bot_menu(application) -> None:
    """Registers commands to the Telegram bottom menu button."""
    commands = [
        BotCommand("download", "Unduh video dari link Vidara"),
        BotCommand("status", "Cek status bot, server, dan kapasitas disk VPS"),
        BotCommand("start", "Mulai bot & panduan penggunaan"),
        BotCommand("help", "Bantuan & daftar perintah"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot command menu registered successfully.")
    except Exception as e:
        logger.warning(f"Failed to set bot commands menu: {e}")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    mode_text = (
        "🚀 <b>Local Bot API (Aktif)</b> - Maksimal s.d <b>2.000 MB (2 GB)</b>"
        if LOCAL_BOT_API_URL else
        "☁️ <b>Cloud Bot API</b> - Maksimal <b>50 MB</b>"
    )

    welcome_text = (
        "👋 <b>Halo! Selamat datang di Vidara Downloader Bot.</b>\n\n"
        "Saya dapat membantu Anda mengunduh video dari Vidara (<code>vidara.to</code> / <code>vidara.so</code>) "
        "langsung ke chat Telegram ini tanpa iklan dan dengan kualitas orisinal!\n\n"
        "📋 <b>Daftar Menu Perintah:</b>\n"
        "• <code>/download &lt;link&gt;</code> : Mengunduh video dari tautan Vidara.\n"
        "• <code>/status</code> : Melihat kondisi server VPS, RAM, disk, & proses aktif.\n"
        "• <code>/help</code> : Panduan cara menggunakan bot.\n\n"
        "💡 <i>Tips: Anda juga bisa langsung menempelkan (paste) link Vidara ke obrolan ini tanpa mengetik /download.</i>\n\n"
        f"⚙️ <b>Mode Server:</b>\n{mode_text}"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    help_text = (
        "📖 <b>Panduan Penggunaan Bot Vidara:</b>\n\n"
        "1. <b>Cara Mengunduh Video:</b>\n"
        "   Ketik: <code>/download https://vidara.to/v/xxxx</code>\n"
        "   Atau cukup kirimkan tautan langsung: <code>vidara.to/v/xxxx</code>\n\n"
        "2. <b>Mengecek Status Bot:</b>\n"
        "   Ketik <code>/status</code> untuk melihat apakah bot sedang aktif, ruang disk VPS, dan antrean unduhan.\n\n"
        "3. <b>Progres Transparan:</b>\n"
        "   Saat proses unduh berjalan, pesan di chat akan diperbarui secara otomatis setiap beberapa detik memperlihatkan jumlah MB yang berhasil diunduh."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /status command, displaying health, disk space, and active jobs."""
    # Disk usage
    total, used, free = shutil.disk_usage(DOWNLOAD_DIR)
    total_gb = total / (1024 ** 3)
    used_gb = used / (1024 ** 3)
    free_gb = free / (1024 ** 3)

    # Server mode
    if LOCAL_BOT_API_URL:
        server_mode = f"🟢 <b>Local Bot API Server</b> (Port 8081)\n   📦 Batas File: <b>{MAX_FILE_SIZE_MB} MB (2 GB)</b>"
    else:
        server_mode = f"🟡 <b>Telegram Cloud API</b>\n   📦 Batas File: <b>{MAX_FILE_SIZE_MB} MB</b>"

    # Active downloads
    active_count = len(ACTIVE_DOWNLOADS)
    if active_count > 0:
        active_list = "\n".join([f"• <i>{info.get('title', 'Video')}</i> ({info.get('progress', '0 MB')})" for info in ACTIVE_DOWNLOADS.values()])
        activity_str = f"⏳ <b>Sedang Berjalan ({active_count} proses):</b>\n{active_list}"
    else:
        activity_str = "💤 <b>Aktivitas:</b> Tidak ada unduhan aktif (Standby)"

    status_message = (
        "🖥️ <b>STATUS SISTEM BOT VIDARA</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ <b>Uptime Bot:</b> <code>{get_uptime_str()}</code>\n"
        f"⚙️ <b>Mode Koneksi:</b>\n{server_mode}\n\n"
        f"💾 <b>Penyimpanan VPS:</b>\n"
        f"   • Total   : <code>{total_gb:.1f} GB</code>\n"
        f"   • Terpakai: <code>{used_gb:.1f} GB</code>\n"
        f"   • Sisa    : <code>{free_gb:.1f} GB (Aman)</code>\n\n"
        f"{activity_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <i>Semua sistem berfungsi normal dan siap menerima link.</i>"
    )
    await update.message.reply_text(status_message, parse_mode=ParseMode.HTML)


async def process_video_download(update: Update, target_url: str):
    """Core logic to download from Vidara and send to Telegram with live progress."""
    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text(
        "🔍 <b>[1/3] Menghubungkan ke Vidara & memeriksa metadata...</b>",
        parse_mode=ParseMode.HTML
    )
    file_path = None
    title = "Video Vidara"

    # Register in active downloads
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
            f"⚡ Mode: Stream-Copy (Kualitas Asli)\n"
            f"⏱️ Status: Berjalan lancar",
            parse_mode=ParseMode.HTML
        )

        # 2. Background task to report live download progress
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
                        if abs(current_mb - last_reported_mb) >= 0.8:
                            last_reported_mb = current_mb
                            await status_msg.edit_text(
                                f"🎬 <b>{title}</b>\n\n"
                                f"⏳ <b>[2/3] Sedang mengunduh stream video ke VPS...</b>\n"
                                f"📊 Terunduh: <code>{current_mb:.1f} MB</code>\n"
                                f"⚡ Mode: Stream-Copy FFmpeg (Kualitas Asli)\n"
                                f"⏱️ Status: Mengambil potongan video...",
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

        # Check final file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"Downloaded '{title}' ({file_size_mb:.2f} MB)")

        # File size check against Telegram limits
        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"⚠️ <b>Ukuran file terlalu besar!</b>\n\n"
                f"Judul: <b>{title}</b>\n"
                f"Ukuran: <code>{file_size_mb:.2f} MB</code>\n\n"
                f"Batas upload bot saat ini adalah <b>{MAX_FILE_SIZE_MB} MB</b>.\n"
                f"<i>(Aktifkan Local Bot API Server di VPS untuk mengizinkan s.d 2000 MB / 2 GB).</i>",
                parse_mode=ParseMode.HTML
            )
            return

        # 4. Notify uploading
        await status_msg.edit_text(
            f"🎬 <b>{title}</b>\n\n"
            f"📤 <b>[3/3] Selesai diunduh ({file_size_mb:.1f} MB)!</b>\n"
            f"Sedang mengunggah file video ke obrolan Telegram Anda...",
            parse_mode=ParseMode.HTML
        )

        caption = (
            f"🎬 <b>{title}</b>\n"
            f"📦 Ukuran: <code>{file_size_mb:.2f} MB</code>\n"
            f"🔗 <a href='{target_url}'>Tautan Sumber</a>"
        )

        with open(file_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
                read_timeout=900,
                write_timeout=900,
                connect_timeout=60
            )

        # Remove the status message after sending
        await status_msg.delete()

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
        # Cleanup temporary files on VPS to keep disk clean
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except OSError as cleanup_err:
                logger.warning(f"Failed to delete {file_path}: {cleanup_err}")


async def download_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /download <url>."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Format perintah salah!</b>\n\n"
            "Gunakan format: <code>/download &lt;link_vidara&gt;</code>\n"
            "<i>Contoh:</i> <code>/download https://vidara.to/v/WJ0DOTFNCx4cg</code>",
            parse_mode=ParseMode.HTML
        )
        return

    raw_url = context.args[0].strip()
    match = VIDARA_URL_PATTERN.search(raw_url)
    if not match:
        await update.message.reply_text(
            "❌ <b>URL tidak valid!</b>\nPastikan tautan berasal dari <code>vidara.to</code> atau <code>vidara.so</code>.",
            parse_mode=ParseMode.HTML
        )
        return

    target_url = match.group(0)
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    await process_video_download(update, target_url)


async def message_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches messages that contain a Vidara link directly."""
    text = update.message.text or ""
    match = VIDARA_URL_PATTERN.search(text)
    if match:
        target_url = match.group(0)
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
        await process_video_download(update, target_url)


def is_local_api_running(base_url: str) -> bool:
    """Checks if the local bot API endpoint is actually responsive."""
    import urllib.request
    from urllib.parse import urlparse
    try:
        parsed = urlparse(base_url)
        test_url = f"{parsed.scheme}://{parsed.netloc}/"
        with urllib.request.urlopen(test_url, timeout=2.0) as resp:
            return True
    except Exception:
        return False


def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("=" * 60)
        print("ERROR: TELEGRAM_BOT_TOKEN belum disetel!")
        print("Buka file .env dan masukkan token bot Anda dari @BotFather.")
        print("=" * 60)
        return

    print("🚀 Menginisialisasi Vidara Downloader Telegram Bot...")
    builder = ApplicationBuilder().token(BOT_TOKEN).post_init(set_bot_menu)

    if LOCAL_BOT_API_URL:
        if is_local_api_running(LOCAL_BOT_API_URL):
            builder = builder.base_url(LOCAL_BOT_API_URL).local_mode(True)
            print(f"📡 Mode: LOCAL BOT API SERVER AKTIF ({LOCAL_BOT_API_URL})")
            print(f"📦 Batas ukuran file: {MAX_FILE_SIZE_MB} MB (s.d 2 GB)")
        else:
            print("=" * 60)
            print(f"⚠️ PERINGATAN: Local Bot API di {LOCAL_BOT_API_URL} tidak merespons (Docker mungkin belum jalan).")
            print("🚀 Otomatis beralih ke TELEGRAM CLOUD SERVER agar bot tetap aktif dan merespons obrolan!")
            print("=" * 60)
            globals()["LOCAL_BOT_API_URL"] = ""
            globals()["MAX_FILE_SIZE_MB"] = 50
    else:
        print(f"☁️ Mode: TELEGRAM CLOUD SERVER (Batas default: {MAX_FILE_SIZE_MB} MB)")

    app = builder.build()

    # Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("download", download_command_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_url_handler))

    print("🤖 Bot Telegram aktif dan menu perintah berhasil dipasang!")
    app.run_polling()


if __name__ == "__main__":
    main()
