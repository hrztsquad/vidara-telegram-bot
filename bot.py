#!/usr/bin/env python3
"""
Telegram Bot for downloading Vidara videos.
Seamlessly integrates VidaraEngine with python-telegram-bot.
"""

import os
import re
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
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


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    welcome_text = (
        "👋 <b>Halo! Selamat datang di Vidara Downloader Bot.</b>\n\n"
        "Saya dapat membantu Anda mengunduh video dari Vidara (<code>vidara.to</code> / <code>vidara.so</code>) "
        "langsung ke chat Telegram ini tanpa iklan!\n\n"
        "📌 <b>Cara Penggunaan:</b>\n"
        "1. Kirim perintah: <code>/download &lt;link_video&gt;</code>\n"
        "   <i>Contoh:</i> <code>/download https://vidara.to/e/WJ0DOTFNCx4cg</code>\n\n"
        "2. Atau cukup <b>kirim/paste link Vidara langsung</b> ke chat ini.\n\n"
        "💡 <i>Catatan: Telegram Bot membatasi ukuran file upload maksimal 50 MB untuk server bot standar.</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    help_text = (
        "📖 <b>Panduan Penggunaan Bot:</b>\n\n"
        "• <code>/download &lt;link&gt;</code> : Mengunduh video dari URL Vidara yang diberikan.\n"
        "• <code>/help</code> : Menampilkan panduan bantuan ini.\n"
        "• <code>/start</code> : Memulai bot & info umum.\n\n"
        "Anda juga bisa langsung mengirimkan link video Vidara tanpa perintah /download."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def process_video_download(update: Update, target_url: str):
    """Core logic to download from Vidara and send to Telegram."""
    status_msg = await update.message.reply_text(
        "🔍 <i>Memeriksa link dan mengambil informasi video...</i>",
        parse_mode=ParseMode.HTML
    )
    file_path = None

    try:
        loop = asyncio.get_running_loop()
        engine = VidaraEngine(output_dir=DOWNLOAD_DIR)

        await status_msg.edit_text(
            "⏳ <i>Mengunduh video via FFmpeg ke server VPS...</i>",
            parse_mode=ParseMode.HTML
        )

        def download_worker():
            metadata = engine.fetch_video_data(target_url)
            saved_path = engine.process_download(metadata)
            return saved_path, metadata

        # Execute blocking download inside threadpool
        file_path, metadata = await loop.run_in_executor(None, download_worker)

        if not file_path or not os.path.exists(file_path):
            raise RuntimeError("File hasil unduhan tidak ditemukan di server.")

        # Check file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        title = metadata.title or metadata.filecode or "Vidara Video"

        logger.info(f"Downloaded '{title}' ({file_size_mb:.2f} MB)")

        # File size check
        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"⚠️ <b>Ukuran file terlalu besar!</b>\n\n"
                f"Judul: <b>{title}</b>\n"
                f"Ukuran: <code>{file_size_mb:.2f} MB</code>\n\n"
                f"Batas upload bot saat ini adalah <b>{MAX_FILE_SIZE_MB} MB</b>.",
                parse_mode=ParseMode.HTML
            )
            return

        await status_msg.edit_text(
            f"📤 <i>Mengunggah ke Telegram ({file_size_mb:.1f} MB)...</i>",
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
                read_timeout=600,
                write_timeout=600,
                connect_timeout=60
            )

        # Remove the status message after sending
        await status_msg.delete()

    except Exception as exc:
        logger.error(f"Error handling download for {target_url}: {exc}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Terjadi kesalahan saat memproses unduhan:</b>\n<code>{str(exc)}</code>",
            parse_mode=ParseMode.HTML
        )

    finally:
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
            "<i>Contoh:</i> <code>/download https://vidara.to/e/WJ0DOTFNCx4cg</code>",
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


def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("=" * 60)
        print("ERROR: TELEGRAM_BOT_TOKEN belum disetel!")
        print("Buka file .env dan masukkan token bot Anda dari @BotFather.")
        print("=" * 60)
        return

    print("🚀 Menginisialisasi Vidara Downloader Telegram Bot...")
    builder = ApplicationBuilder().token(BOT_TOKEN)

    if LOCAL_BOT_API_URL:
        # local_mode allows local file handling directly without HTTP re-upload
        builder = builder.base_url(LOCAL_BOT_API_URL).local_mode(True)
        print(f"📡 Mode: LOCAL BOT API SERVER ({LOCAL_BOT_API_URL})")
        print(f"📦 Batas ukuran file: {MAX_FILE_SIZE_MB} MB (s.d 2 GB)")
    else:
        print(f"☁️ Mode: TELEGRAM CLOUD SERVER (Batas default: {MAX_FILE_SIZE_MB} MB)")

    app = builder.build()

    # Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("download", download_command_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_url_handler))

    print("🤖 Bot Telegram aktif dan siap menerima perintah!")
    app.run_polling()


if __name__ == "__main__":
    main()
