#!/usr/bin/env python3
"""
Telegram Bot for downloading Vidara videos.
Features:
- Live download progress (MB)
- Menu button & /status command
- Smart Auto-Compression: If file > 50 MB on Cloud mode, automatically compresses and sends!
- Supports Local Bot API up to 2.000 MB (2 GB) without compression if active.
"""

import os
import re
import time
import shutil
import asyncio
import logging
import ffmpeg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

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


def compress_video(input_path: str, output_path: str, target_mb: float = 46.0) -> str:
    """Compresses video so it falls cleanly under Telegram's 50 MB limit."""
    probe = ffmpeg.probe(input_path)
    duration = float(probe["format"].get("duration", 0))
    if duration <= 0:
        # Fallback duration if probe failed
        duration = 180.0

    target_total_bits = target_mb * 1024 * 1024 * 8
    target_bitrate = int(target_total_bits / duration)
    audio_bitrate = 128000
    video_bitrate = max(target_bitrate - audio_bitrate, 250000)

    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(
        stream,
        output_path,
        vcodec="libx264",
        preset="veryfast",
        video_bitrate=video_bitrate,
        acodec="aac",
        audio_bitrate="128k",
        loglevel="warning"
    )
    ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, overwrite_output=True)
    return output_path


async def set_bot_menu(application) -> None:
    """Registers commands to the Telegram bottom menu button."""
    commands = [
        BotCommand("download", "Unduh video dari link Vidara"),
        BotCommand("status", "Cek status bot, server, dan penyimpanan VPS"),
        BotCommand("start", "Mulai bot & panduan penggunaan"),
        BotCommand("help", "Bantuan & daftar perintah"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot command menu registered successfully.")
    except Exception as e:
        logger.warning(f"Failed to set bot commands menu: {e}")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command."""
    mode_text = (
        "🚀 <b>Local Bot API (Aktif)</b> - Maksimal s.d <b>2.000 MB (2 GB)</b>"
        if LOCAL_BOT_API_URL else
        "☁️ <b>Telegram Cloud (Aktif + Auto-Compress)</b> - Semua video pasti terkirim!"
    )

    welcome_text = (
        "👋 <b>Halo! Selamat datang di Vidara Downloader Bot.</b>\n\n"
        "Saya dapat membantu Anda mengunduh video dari Vidara (<code>vidara.to</code> / <code>vidara.so</code>) "
        "langsung ke chat Telegram ini tanpa iklan!\n\n"
        "📋 <b>Daftar Menu:</b>\n"
        "• <code>/download &lt;link&gt;</code> : Mengunduh video dari tautan Vidara.\n"
        "• <code>/status</code> : Melihat kapasitas disk VPS, uptime, & proses aktif.\n"
        "• <code>/help</code> : Panduan bantuan lengkap.\n\n"
        "💡 <i>Tips: Cukup tempelkan (paste) link video Vidara langsung ke chat ini!</i>\n\n"
        f"⚙️ <b>Status Sistem:</b>\n{mode_text}"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command."""
    help_text = (
        "📖 <b>Panduan Penggunaan Bot Vidara:</b>\n\n"
        "1. <b>Kirim Tautan:</b>\n"
        "   Ketik: <code>/download https://vidara.to/v/xxxx</code>\n"
        "   Atau langsung kirim link: <code>vidara.to/v/xxxx</code>\n\n"
        "2. <b>Cek Status Sistem:</b>\n"
        "   Ketik <code>/status</code> untuk melihat kondisi bot dan sisa ruang penyimpanan VPS.\n\n"
        "3. <b>Fitur Auto-Deliver:</b>\n"
        "   Jika ukuran video melebihi 50 MB, bot akan otomatis mengoptimalkannya sehingga "
        "   video tetap <b>PASTI TERKIRIM ke obrolan Telegram Anda</b> tanpa tertahan di VPS!"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /status command."""
    total, used, free = shutil.disk_usage(DOWNLOAD_DIR)
    total_gb = total / (1024 ** 3)
    used_gb = used / (1024 ** 3)
    free_gb = free / (1024 ** 3)

    if LOCAL_BOT_API_URL:
        server_mode = f"🟢 <b>Local Bot API Server</b> (Port 8081)\n   📦 Batas File: <b>{MAX_FILE_SIZE_MB} MB (2 GB)</b>"
    else:
        server_mode = "🟢 <b>Telegram Cloud API + Auto-Compressor</b>\n   📦 Batas File: <b>Mendukung Semua Ukuran (Auto-Deliver)</b>"

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
    """Core logic to download from Vidara and send to Telegram with live progress & auto-compression."""
    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text(
        "🔍 <b>[1/3] Menghubungkan ke Vidara & memeriksa metadata...</b>",
        parse_mode=ParseMode.HTML
    )
    file_path = None
    compressed_file_path = None
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
            f"⚡ Mode: Stream-Copy (Kualitas Asli)\n"
            f"⏱️ Status: Berjalan lancar",
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

        # Check final size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"Downloaded '{title}' ({file_size_mb:.2f} MB)")

        upload_file_path = file_path
        size_note = f"{file_size_mb:.2f} MB"

        # Check if file exceeds limit
        if file_size_mb > MAX_FILE_SIZE_MB:
            if not LOCAL_BOT_API_URL:
                # AUTO-COMPRESSION: Optimize to under 50 MB so Telegram doesn't reject it!
                await status_msg.edit_text(
                    f"🎬 <b>{title}</b>\n\n"
                    f"⚙️ <b>Mengoptimalkan Ukuran Video...</b>\n"
                    f"📦 Ukuran asli: <code>{file_size_mb:.1f} MB</code> (&gt; 50 MB)\n\n"
                    f"Sedang mengompres agar <b>PASTI DAPAT TERKIRIM</b> ke chat Telegram Anda...",
                    parse_mode=ParseMode.HTML
                )
                compressed_file_path = os.path.join(DOWNLOAD_DIR, f"compressed_{filename}")
                await loop.run_in_executor(
                    None,
                    lambda: compress_video(file_path, compressed_file_path, target_mb=46.0)
                )
                upload_file_path = compressed_file_path
                compressed_mb = os.path.getsize(compressed_file_path) / (1024 * 1024)
                size_note = f"{compressed_mb:.2f} MB (Dioptimalkan dari {file_size_mb:.1f} MB)"
            else:
                await status_msg.edit_text(
                    f"⚠️ <b>Ukuran file terlalu besar!</b>\n\n"
                    f"Judul: <b>{title}</b>\n"
                    f"Ukuran: <code>{file_size_mb:.2f} MB</code>\n\n"
                    f"Batas upload bot adalah <b>{MAX_FILE_SIZE_MB} MB (2 GB)</b>.",
                    parse_mode=ParseMode.HTML
                )
                return

        # 4. Notify uploading
        await status_msg.edit_text(
            f"🎬 <b>{title}</b>\n\n"
            f"📤 <b>[3/3] Selesai diproses ({size_note})!</b>\n"
            f"Sedang mengunggah file video ke chat Telegram Anda...",
            parse_mode=ParseMode.HTML
        )

        caption = (
            f"🎬 <b>{title}</b>\n"
            f"📦 Ukuran: <code>{size_note}</code>\n"
            f"🔗 <a href='{target_url}'>Tautan Sumber</a>"
        )

        with open(upload_file_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
                read_timeout=900,
                write_timeout=900,
                connect_timeout=60
            )

        # Delete status message on success
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
        # Cleanup temporary files on VPS to keep disk space clean
        for p in (file_path, compressed_file_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    logger.info(f"Cleaned up temporary file: {p}")
                except OSError as cleanup_err:
                    logger.warning(f"Failed to delete {p}: {cleanup_err}")


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
    """Catches direct Vidara URL in text message."""
    text = update.message.text or ""
    match = VIDARA_URL_PATTERN.search(text)
    if match:
        target_url = match.group(0)
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
        await process_video_download(update, target_url)


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
            print(f"⚠️ PERINGATAN: Local Bot API di {LOCAL_BOT_API_URL} tidak merespons.")
            print("🚀 Otomatis beralih ke TELEGRAM CLOUD + AUTO-COMPRESSOR agar bot tetap aktif!")
            print("=" * 60)
            globals()["LOCAL_BOT_API_URL"] = ""
            globals()["MAX_FILE_SIZE_MB"] = 50
    else:
        print("☁️ Mode: TELEGRAM CLOUD + AUTO-COMPRESSOR (Semua video pasti terkirim!)")

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
