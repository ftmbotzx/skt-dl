"""
Implements download functionality for YouTube streams
"""

import os
import time
import logging
import shutil
from typing import Dict, Optional, Callable, Tuple, List, Union

import requests

from .exceptions import DownloadError, VideoUnavailableError
from .utils import (
    safe_filename, 
    format_filesize, 
    calculate_eta, 
    create_progress_bar
)
from .constants import DOWNLOAD_CHUNK_SIZE
from .extractor import YouTubeExtractor
from .api_extractor import YouTubeAPIExtractor

logger = logging.getLogger('skt-dl.downloader')


class VideoDownloader:
    """
    Class for downloading YouTube videos
    """
    
    def __init__(self, extractor=None):
        """
        Initialize the downloader
        
        Args:
            extractor: Optional extractor instance to use (YouTubeExtractor or YouTubeAPIExtractor)
        """
        if extractor is None:
            # Try to create API extractor first, fall back to regular extractor if no API key
            try:
                self.extractor = YouTubeAPIExtractor()
            except ValueError:
                self.extractor = YouTubeExtractor()
        else:
            self.extractor = extractor
            
        self.session = requests.Session()
    
    def download_video(
        self,
        url: str,
        output_path: str = ".",
        quality: str = "best",
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Download a YouTube video
        
        Args:
            url: YouTube video URL or ID
            output_path: Directory to save the downloaded file
            quality: Quality to download (e.g., "best", "worst", "720p")
            progress_callback: Optional callback for progress updates
            filename: Optional custom filename (without extension)
            
        Returns:
            Path to the downloaded file
            
        Raises:
            VideoUnavailableError: If the video is unavailable
            DownloadError: If the download fails
        """
        logger.info(f"Downloading video from {url}")
        
        # Extract video info
        video_info = self.extractor.extract_video_info(url)
        
        # Select the format to download
        format_to_download = self._select_format(video_info["formats"], quality)
        
        if not format_to_download:
            raise DownloadError(f"No suitable format found for quality: {quality}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Determine filename
        if not filename:
            title = safe_filename(video_info["title"])
            filename = title
        
        # Add appropriate extension
        container = format_to_download.get("container", "mp4")
        full_filename = f"{filename}.{container}"
        output_file = os.path.join(output_path, full_filename)
        
        # Log download details
        content_length = format_to_download.get("content_length", 0)
        logger.info(
            f"Downloading format: {format_to_download['quality']}, "
            f"size: {format_filesize(content_length)}, "
            f"to: {output_file}"
        )
        
        # Download the file
        try:
            self._download_stream(
                format_to_download["url"],
                output_file,
                content_length,
                progress_callback
            )
            
            logger.info(f"Download completed: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            # Clean up partial file if download failed
            if os.path.exists(output_file):
                os.remove(output_file)
            raise DownloadError(f"Download failed: {str(e)}")
    
    def download_playlist(
        self,
        playlist_url: str,
        output_path: str = ".",
        quality: str = "best",
        progress_callback: Optional[Callable[[int, int, str, int, int, float], None]] = None
    ) -> List[str]:
        """
        Download all videos in a YouTube playlist
        
        Args:
            playlist_url: YouTube playlist URL
            output_path: Directory to save the downloaded files
            quality: Quality to download (e.g., "best", "worst", "720p")
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of paths to the downloaded files
            
        Raises:
            PlaylistUnavailableError: If the playlist is unavailable
            DownloadError: If the download fails
        """
        logger.info(f"Downloading playlist: {playlist_url}")
        
        # Extract playlist info
        playlist_info = self.extractor.extract_playlist_videos(playlist_url)
        
        # Create playlist directory
        playlist_title = safe_filename(playlist_info["title"])
        playlist_dir = os.path.join(output_path, playlist_title)
        os.makedirs(playlist_dir, exist_ok=True)
        
        videos = playlist_info["videos"]
        total_videos = len(videos)
        downloaded_files = []
        
        logger.info(f"Found {total_videos} videos in playlist")
        
        # Download each video
        for i, video in enumerate(videos, 1):
            video_id = video["id"]
            video_title = video["title"]
            
            logger.info(f"Downloading video {i}/{total_videos}: {video_title}")
            
            try:
                # Create a wrapped progress callback that includes playlist progress
                wrapped_callback = None
                if progress_callback:
                    def wrapped_callback(bytes_downloaded, total_bytes, elapsed):
                        progress_callback(
                            i, total_videos, video_title, 
                            bytes_downloaded, total_bytes, elapsed
                        )
                
                # Download the video
                file_path = self.download_video(
                    video_id,
                    output_path=playlist_dir,
                    quality=quality,
                    progress_callback=wrapped_callback
                )
                
                downloaded_files.append(file_path)
                
            except (VideoUnavailableError, DownloadError) as e:
                logger.warning(f"Failed to download video {video_id}: {str(e)}")
                # Continue with next video even if one fails
                continue
        
        if not downloaded_files:
            raise DownloadError("Failed to download any videos from the playlist")
        
        logger.info(f"Playlist download completed: {len(downloaded_files)}/{total_videos} videos")
        return downloaded_files
    
    def _select_format(self, formats: List[Dict], quality: str) -> Optional[Dict]:
        """
        Select the best format based on requested quality
        
        Args:
            formats: List of available formats
            quality: Requested quality string
            
        Returns:
            Selected format dictionary or None if no suitable format found
        """
        # Filter formats to include only those with both audio and video
        combined_formats = [fmt for fmt in formats if fmt["is_audio"] and fmt["is_video"]]
        
        # If no combined formats, try formats with only video
        if not combined_formats:
            video_formats = [fmt for fmt in formats if fmt["is_video"]]
            if video_formats:
                logger.info("No combined formats found. Using video-only format.")
                return sorted(video_formats, key=lambda fmt: fmt.get("height", 0), reverse=True)[0]
            return None
        
        if quality == "best":
            # Sort by resolution (height) in descending order
            sorted_formats = sorted(
                combined_formats,
                key=lambda fmt: (fmt.get("height", 0), fmt.get("video_bitrate", 0)),
                reverse=True
            )
            return sorted_formats[0] if sorted_formats else None
            
        elif quality == "worst":
            # Sort by resolution (height) in ascending order
            sorted_formats = sorted(
                combined_formats,
                key=lambda fmt: (fmt.get("height", 0), fmt.get("video_bitrate", 0))
            )
            return sorted_formats[0] if sorted_formats else None
            
        else:
            # Try to match the requested quality (e.g., "720p")
            quality_height = 0
            
            # Extract height from quality string (e.g., "720p" -> 720)
            if quality.lower().endswith("p"):
                try:
                    quality_height = int(quality[:-1])
                except ValueError:
                    pass
            
            if quality_height > 0:
                # Find formats matching the requested height
                matching_formats = [
                    fmt for fmt in combined_formats 
                    if fmt.get("height", 0) == quality_height
                ]
                
                if matching_formats:
                    # Sort matching formats by bitrate in descending order
                    sorted_formats = sorted(
                        matching_formats,
                        key=lambda fmt: fmt.get("video_bitrate", 0),
                        reverse=True
                    )
                    return sorted_formats[0]
            
            # If no exact match, find the closest format below the requested quality
            lower_formats = [
                fmt for fmt in combined_formats 
                if fmt.get("height", 0) < quality_height
            ]
            
            if lower_formats:
                # Get the highest format below the requested quality
                sorted_formats = sorted(
                    lower_formats,
                    key=lambda fmt: fmt.get("height", 0),
                    reverse=True
                )
                return sorted_formats[0]
            
            # If no suitable format found, return the best available
            sorted_formats = sorted(
                combined_formats,
                key=lambda fmt: (fmt.get("height", 0), fmt.get("video_bitrate", 0)),
                reverse=True
            )
            return sorted_formats[0] if sorted_formats else None
    
    def _download_stream(
        self,
        url: str,
        output_file: str,
        content_length: int,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> None:
        """
        Download a stream from a URL with progress reporting
        
        Args:
            url: URL to download
            output_file: Path to save the downloaded file
            content_length: Expected content length in bytes
            progress_callback: Optional callback for progress updates
            
        Raises:
            DownloadError: If the download fails
        """
        try:
            # Make a streaming request
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # If content length wasn't provided, try to get it from response headers
            if content_length == 0:
                content_length = int(response.headers.get('content-length', 0))
            
            # Initialize progress tracking
            bytes_downloaded = 0
            start_time = time.time()
            
            # Open file for writing
            with open(output_file, 'wb') as f:
                # Download in chunks
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if not chunk:
                        continue
                    
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Update progress
                    if progress_callback:
                        elapsed = time.time() - start_time
                        progress_callback(bytes_downloaded, content_length, elapsed)
            
            # Final progress update
            if progress_callback and content_length > 0:
                elapsed = time.time() - start_time
                progress_callback(content_length, content_length, elapsed)
                
        except (requests.RequestException, IOError) as e:
            raise DownloadError(f"Download failed: {str(e)}")


def default_progress_callback(
    bytes_downloaded: int,
    total_bytes: int,
    elapsed: float,
    file_index: int = 1,
    total_files: int = 1,
    current_title: str = ""
) -> None:
    """
    Default progress callback function
    
    Args:
        bytes_downloaded: Number of bytes downloaded
        total_bytes: Total number of bytes
        elapsed: Time elapsed in seconds
        file_index: Current file index (for playlists)
        total_files: Total number of files (for playlists)
        current_title: Title of the current file being downloaded
    """
    if total_bytes > 0:
        percent = (bytes_downloaded / total_bytes) * 100
        downloaded_mb = bytes_downloaded / 1024 / 1024
        total_mb = total_bytes / 1024 / 1024
        
        speed = bytes_downloaded / (elapsed or 0.1) / 1024
        unit = "KB/s"
        
        if speed >= 1024:
            speed /= 1024
            unit = "MB/s"
        
        eta = calculate_eta(time.time() - elapsed, bytes_downloaded, total_bytes)
        progress_bar = create_progress_bar(bytes_downloaded, total_bytes)
        
        if total_files > 1:
            status = (
                f"File {file_index}/{total_files} | {current_title} | "
                f"{progress_bar} | "
                f"{downloaded_mb:.1f}MB/{total_mb:.1f}MB | "
                f"{speed:.1f}{unit} | ETA: {eta}"
            )
        else:
            status = (
                f"{progress_bar} | "
                f"{downloaded_mb:.1f}MB/{total_mb:.1f}MB | "
                f"{speed:.1f}{unit} | ETA: {eta}"
            )
        
        # Clear line and print status
        print(f"\r{status}", end="", flush=True)
        
        # Print newline when done
        if bytes_downloaded >= total_bytes:
            print()
    else:
        # When total size is unknown
        downloaded_mb = bytes_downloaded / 1024 / 1024
        speed = bytes_downloaded / (elapsed or 0.1) / 1024
        unit = "KB/s"
        
        if speed >= 1024:
            speed /= 1024
            unit = "MB/s"
        
        if total_files > 1:
            status = (
                f"File {file_index}/{total_files} | {current_title} | "
                f"Downloaded: {downloaded_mb:.1f}MB | "
                f"{speed:.1f}{unit}"
            )
        else:
            status = f"Downloaded: {downloaded_mb:.1f}MB | {speed:.1f}{unit}"
        
        print(f"\r{status}", end="", flush=True)
