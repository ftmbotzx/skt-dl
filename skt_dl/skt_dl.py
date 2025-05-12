"""
Command-line interface for skt-dl
"""

import os
import sys
import argparse
import logging
from typing import List, Optional

from .downloader import VideoDownloader, default_progress_callback
from .exceptions import (
    ExtractionError,
    DownloadError,
    VideoUnavailableError,
    PlaylistUnavailableError
)

logger = logging.getLogger('skt-dl.cli')


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="skt-dl - YouTube Video Downloader",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "url",
        help="YouTube URL to download (video or playlist)"
    )
    
    parser.add_argument(
        "-o", "--output-path",
        help="Directory to save downloaded files",
        default="."
    )
    
    parser.add_argument(
        "-q", "--quality",
        help="Video quality to download (e.g., best, worst, 720p, 1080p)",
        default="best"
    )
    
    parser.add_argument(
        "-f", "--filename",
        help="Custom filename for the downloaded file (without extension)"
    )
    
    parser.add_argument(
        "--playlist",
        help="Force URL to be treated as a playlist",
        action="store_true"
    )
    
    parser.add_argument(
        "--no-playlist",
        help="Force URL to be treated as a single video",
        action="store_true"
    )
    
    parser.add_argument(
        "--verbose",
        help="Enable verbose logging",
        action="store_true"
    )
    
    parser.add_argument(
        "--version",
        help="Show version information and exit",
        action="store_true"
    )
    
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    """
    Configure logging based on verbosity level
    
    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def show_version() -> None:
    """
    Display version information
    """
    from . import __version__
    print(f"skt-dl version {__version__}")
    print("A custom YouTube video and playlist downloader")
    sys.exit(0)


def download_video(args: argparse.Namespace) -> None:
    """
    Download a single video
    
    Args:
        args: Parsed command-line arguments
    """
    downloader = VideoDownloader()
    
    try:
        output_file = downloader.download_video(
            args.url,
            output_path=args.output_path,
            quality=args.quality,
            progress_callback=default_progress_callback,
            filename=args.filename
        )
        
        print(f"\nVideo downloaded successfully to: {output_file}")
        
    except VideoUnavailableError as e:
        logger.error(f"Video unavailable: {str(e)}")
        sys.exit(1)
    except DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


def download_playlist(args: argparse.Namespace) -> None:
    """
    Download a playlist
    
    Args:
        args: Parsed command-line arguments
    """
    downloader = VideoDownloader()
    
    try:
        def playlist_progress_callback(
            current_index: int,
            total_videos: int,
            video_title: str,
            bytes_downloaded: int,
            total_bytes: int,
            elapsed: float
        ) -> None:
            default_progress_callback(
                bytes_downloaded,
                total_bytes,
                elapsed,
                current_index,
                total_videos,
                video_title
            )
        
        output_files = downloader.download_playlist(
            args.url,
            output_path=args.output_path,
            quality=args.quality,
            progress_callback=playlist_progress_callback
        )
        
        print(f"\nPlaylist downloaded successfully: {len(output_files)} videos")
        
    except PlaylistUnavailableError as e:
        logger.error(f"Playlist unavailable: {str(e)}")
        sys.exit(1)
    except DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


def guess_download_type(url: str) -> str:
    """
    Guess if the URL is a video or playlist
    
    Args:
        url: YouTube URL
        
    Returns:
        Type of URL ("video" or "playlist")
    """
    if "list=" in url:
        return "playlist"
    else:
        return "video"


def main() -> None:
    """
    Main CLI entry point
    """
    # Check for --version flag before parsing other arguments
    if "--version" in sys.argv:
        show_version()
        
    args = parse_arguments()
    
    # Display version and exit if requested
    if args.version:
        show_version()
    
    # Configure logging
    configure_logging(args.verbose)
    
    # Determine if URL is a video or playlist
    if args.no_playlist:
        download_type = "video"
    elif args.playlist:
        download_type = "playlist"
    else:
        download_type = guess_download_type(args.url)
    
    # Download based on determined type
    if download_type == "video":
        download_video(args)
    else:
        download_playlist(args)


if __name__ == "__main__":
    main()