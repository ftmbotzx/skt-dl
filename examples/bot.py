#!/usr/bin/env python3
"""
Simple example of using YoutubeDL from skt-dl in a Telegram bot

This is a minimal example showing how to use the YoutubeDL class from skt-dl
to download YouTube videos, similar to how you would use youtube-dl or yt-dlp.
"""

import os
import logging
from skt_dl import YoutubeDL  # Import YoutubeDL from skt-dl

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example function to download a YouTube video
def download_youtube_video(url, output_dir="downloads"):
    """
    Download a YouTube video using skt-dl
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save the downloaded file
        
    Returns:
        Path to downloaded file or None if download failed
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Options for YoutubeDL (similar to youtube-dl/yt-dlp options)
    options = {
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',  # Output filename template
        'format': 'best',  # Best quality
        'quiet': False,  # Show download progress
        'writesubtitles': True,  # Download subtitles
        'writethumbnail': True,  # Download thumbnail
    }
    
    try:
        # Initialize YoutubeDL with options
        ydl = YoutubeDL(options)
        
        # Extract info and download the video
        info = ydl.extract_info(url, download=True)
        
        if 'error' in info:
            logger.error(f"Error: {info['error']}")
            return None
            
        # Return the path to the downloaded file
        if 'downloaded_file' in info:
            logger.info(f"Downloaded: {info['downloaded_file']}")
            return info['downloaded_file']
        else:
            logger.warning("Video info extracted but file was not downloaded")
            return None
            
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Example function to handle video download in a Telegram bot
def process_youtube_url(url):
    """
    Process a YouTube URL from a Telegram bot
    
    Args:
        url: YouTube video URL sent by user
        
    Returns:
        Dictionary with info about the download
    """
    # Check if the URL is a YouTube URL
    if not ("youtube.com" in url or "youtu.be" in url):
        return {"success": False, "message": "Not a valid YouTube URL"}
        
    # Download the video
    output_file = download_youtube_video(url)
    
    if output_file:
        return {
            "success": True,
            "file_path": output_file,
            "message": f"Downloaded: {os.path.basename(output_file)}"
        }
    else:
        return {
            "success": False,
            "message": "Failed to download video"
        }

# Example usage
if __name__ == "__main__":
    # Example URL - replace with a real YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"Downloading video: {test_url}")
    result = process_youtube_url(test_url)
    
    if result["success"]:
        print(f"Success! {result['message']}")
        print(f"File saved to: {result['file_path']}")
    else:
        print(f"Failed: {result['message']}")