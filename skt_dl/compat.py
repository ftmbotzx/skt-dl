"""
Compatibility module for projects migrating from other YouTube download libraries
"""

import os
import logging
from typing import Dict, List, Optional, Union, Any, Tuple, Callable

from .api_extractor import YouTubeAPIExtractor
from .downloader import VideoDownloader
from .captions import SubtitleDownloader
from .thumbnail import ThumbnailDownloader
from .exceptions import (
    ExtractionError,
    DownloadError,
    VideoUnavailableError,
    PlaylistUnavailableError
)

logger = logging.getLogger('skt-dl.compat')

class YoutubeDL:
    """
    Compatibility class that provides an interface similar to youtube-dl/yt-dlp
    
    This allows for easier migration from youtube-dl or yt-dlp to skt-dl.
    """
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """
        Initialize the YoutubeDL instance
        
        Args:
            options: Dictionary of options similar to youtube-dl options
        """
        self.options = options or {}
        
        # Map options to our internal options
        self.output_path = self.options.get('outtmpl', '.').split('/')[0] or '.'
        if '%' in self.output_path or '{}' in self.output_path:
            # If the output path contains format specifiers, use the current directory
            self.output_path = '.'
            
        self.quiet = self.options.get('quiet', False)
        self.verbose = self.options.get('verbose', False)
        self.format = self.options.get('format', 'best')
        self.write_subs = self.options.get('writesubtitles', False)
        self.write_thumbnail = self.options.get('writethumbnail', False)
        self.download_archive = self.options.get('download_archive')
        
        # Set up logging
        log_level = logging.ERROR if self.quiet else logging.INFO
        if self.verbose:
            log_level = logging.DEBUG
        logging.basicConfig(level=log_level)
        
        # Initialize components
        self.extractor = YouTubeAPIExtractor()
        self.downloader = VideoDownloader(self.extractor)
        self.subtitle_downloader = SubtitleDownloader(self.extractor)
        self.thumbnail_downloader = ThumbnailDownloader(self.extractor)
        
        # Archive for tracking downloaded videos if enabled
        self.downloaded_ids = set()
        if self.download_archive and os.path.exists(self.download_archive):
            try:
                with open(self.download_archive, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.downloaded_ids.add(line.split(' ')[-1])
            except Exception as e:
                logger.warning(f"Error reading download archive: {e}")
    
    def _archive_id(self, video_id: str) -> None:
        """Add a video ID to the download archive if enabled"""
        if not self.download_archive:
            return
            
        self.downloaded_ids.add(video_id)
        try:
            with open(self.download_archive, 'a', encoding='utf-8') as f:
                f.write(f"youtube {video_id}\n")
        except Exception as e:
            logger.warning(f"Error writing to download archive: {e}")
    
    def extract_info(self, url: str, download: bool = True) -> Dict[str, Any]:
        """
        Extract information about a video or playlist
        
        Args:
            url: URL to extract information from
            download: Whether to download the video(s)
            
        Returns:
            Dictionary with video/playlist info
        """
        try:
            # Determine if URL is a playlist
            if 'playlist' in url or 'list=' in url:
                info = self.extractor.extract_playlist_videos(url)
                if download:
                    output_files = []
                    for video in info.get('videos', []):
                        video_id = video.get('id')
                        if video_id in self.downloaded_ids:
                            logger.info(f"Skipping already downloaded video: {video_id}")
                            continue
                            
                        try:
                            output_file = self.downloader.download_video(
                                url=video.get('url'),
                                output_path=self.output_path,
                                quality=self.format
                            )
                            output_files.append(output_file)
                            
                            # Handle subtitles if requested
                            if self.write_subs:
                                self.subtitle_downloader.download_subtitle(
                                    video_url=video.get('url'),
                                    output_path=self.output_path
                                )
                                
                            # Handle thumbnail if requested
                            if self.write_thumbnail:
                                self.thumbnail_downloader.download_thumbnail(
                                    video_url=video.get('url'),
                                    output_path=self.output_path
                                )
                                
                            # Add to archive
                            if video_id:
                                self._archive_id(video_id)
                                
                        except Exception as e:
                            logger.error(f"Error downloading video {video_id}: {e}")
                    
                    # Add download results to info
                    info['downloaded_files'] = output_files
                
                return info
            else:
                # Single video
                info = self.extractor.extract_video_info(url)
                video_id = info.get('id')
                
                if download:
                    # Check if already downloaded
                    if video_id in self.downloaded_ids:
                        logger.info(f"Skipping already downloaded video: {video_id}")
                        info['downloaded'] = False
                        return info
                        
                    # Download video
                    output_file = self.downloader.download_video(
                        url=url,
                        output_path=self.output_path,
                        quality=self.format
                    )
                    info['downloaded_file'] = output_file
                    info['downloaded'] = True
                    
                    # Handle subtitles if requested
                    if self.write_subs:
                        subtitle_file = self.subtitle_downloader.download_subtitle(
                            video_url=url,
                            output_path=self.output_path
                        )
                        info['subtitle_file'] = subtitle_file
                        
                    # Handle thumbnail if requested
                    if self.write_thumbnail:
                        thumbnail_file = self.thumbnail_downloader.download_thumbnail(
                            video_url=url,
                            output_path=self.output_path
                        )
                        info['thumbnail_file'] = thumbnail_file
                        
                    # Add to archive
                    if video_id:
                        self._archive_id(video_id)
                
                return info
                
        except Exception as e:
            logger.error(f"Error extracting info: {e}")
            return {'error': str(e)}
    
    def download(self, url_list: List[str]) -> List[Dict[str, Any]]:
        """
        Download videos from a list of URLs
        
        Args:
            url_list: List of URLs to download
            
        Returns:
            List of dictionaries with download results
        """
        results = []
        for url in url_list:
            try:
                info = self.extract_info(url, download=True)
                results.append(info)
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                results.append({'url': url, 'error': str(e)})
        
        return results