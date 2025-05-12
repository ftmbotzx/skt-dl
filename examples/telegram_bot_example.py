#!/usr/bin/env python3
"""
Example of using skt-dl with a Telegram bot

This script demonstrates how to use the YoutubeDL class from skt-dl
to download YouTube videos through a Telegram bot.

Requirements:
- python-telegram-bot
- skt-dl

Install with:
pip install python-telegram-bot skt-dl
"""

import os
import logging
from typing import Dict, List

# Import YoutubeDL from skt-dl
from skt_dl import YoutubeDL

# Import telegram bot dependencies
# This example uses python-telegram-bot library
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
except ImportError:
    print("To run this example, install python-telegram-bot:")
    print("pip install python-telegram-bot")
    exit(1)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the Telegram bot token from environment variable
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("Please set the TELEGRAM_TOKEN environment variable.")
    exit(1)

# Configure download directory
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# YoutubeDL options
YOUTUBE_DL_OPTIONS = {
    'outtmpl': DOWNLOAD_DIR + '/%(title)s.%(ext)s',
    'format': 'best[filesize<50M]',  # Limit file size to 50MB for Telegram
    'writethumbnail': True,
    'quiet': False,
    'verbose': False,
    'download_archive': DOWNLOAD_DIR + '/archive.txt'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! Send me a YouTube URL and I'll download the video for you."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
    Send me a YouTube video URL, and I'll download it for you.
    
    Commands:
    /start - Start the bot
    /help - Show this help message
    
    Supported URLs:
    - YouTube video URLs (e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ)
    - YouTube playlist URLs (will download first video only)
    """
    await update.message.reply_text(help_text)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a video from the provided URL."""
    url = update.message.text
    
    # Check if the message is a YouTube URL
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text("Please send a valid YouTube URL.")
        return
    
    # Send a waiting message
    await update.message.reply_text("Downloading video... Please wait.")
    
    try:
        # Initialize YoutubeDL with options
        ydl = YoutubeDL(YOUTUBE_DL_OPTIONS)
        
        # Extract video information
        info = ydl.extract_info(url, download=True)
        
        if 'error' in info:
            await update.message.reply_text(f"Error: {info['error']}")
            return
            
        # Check if the file was downloaded successfully
        if 'downloaded_file' in info and info['downloaded']:
            video_file = info['downloaded_file']
            await update.message.reply_text(f"Download complete: {os.path.basename(video_file)}")
            
            # Send the video file
            with open(video_file, 'rb') as f:
                await update.message.reply_video(
                    video=f,
                    caption=info.get('title', 'Downloaded video'),
                    supports_streaming=True
                )
        else:
            # Provide more information if the download failed or wasn't performed
            if 'title' in info:
                await update.message.reply_text(
                    f"Video info extracted: {info['title']}\n"
                    "But download was not completed. File might be too large for Telegram."
                )
            else:
                await update.message.reply_text("Could not download the video.")
    
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        await update.message.reply_text(f"An error occurred: {str(e)}")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()