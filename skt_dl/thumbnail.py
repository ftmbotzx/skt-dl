"""
Module for downloading YouTube video thumbnails
"""

import os
import logging
from typing import Dict, Optional, List, Union, Tuple

import requests

from .utils import safe_filename
from .exceptions import ExtractionError, DownloadError
from .api_extractor import YouTubeAPIExtractor

logger = logging.getLogger('skt-dl.thumbnail')

class ThumbnailDownloader:
    """
    Class for downloading YouTube video thumbnails
    """
    
    def __init__(self, api_extractor: Optional[YouTubeAPIExtractor] = None):
        """
        Initialize the thumbnail downloader
        
        Args:
            api_extractor: Optional YouTubeAPIExtractor instance to use
        """
        self.api_extractor = api_extractor
        self.session = requests.Session()
        
    def get_thumbnail_urls(self, video_url: str) -> Dict[str, str]:
        """
        Get all available thumbnail URLs for a YouTube video
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Dictionary of thumbnail URLs by quality
            
        Raises:
            ExtractionError: If thumbnail info can't be extracted
        """
        logger.info(f"Getting thumbnail URLs for: {video_url}")
        
        if not self.api_extractor:
            logger.warning("API extractor not available, creating one")
            self.api_extractor = YouTubeAPIExtractor()
            
        try:
            # Extract video info using API extractor
            video_info = self.api_extractor.extract_video_info(video_url)
            video_id = video_info.get("id")
            
            # Create thumbnail URLs using standard YouTube patterns
            thumbnail_urls = {
                "maxres": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                "high": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "medium": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                "standard": f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",
                "default": f"https://i.ytimg.com/vi/{video_id}/default.jpg"
            }
            
            # Also get the URL from the API response if available
            if "thumbnail" in video_info and video_info["thumbnail"]:
                thumbnail_urls["api"] = video_info["thumbnail"]
                
            return thumbnail_urls
            
        except Exception as e:
            logger.error(f"Error getting thumbnail URLs: {str(e)}")
            raise ExtractionError(f"Failed to get thumbnail URLs: {str(e)}")
            
    def download_thumbnail(
        self, 
        video_url: str, 
        output_path: str = ".",
        quality: str = "high",
        filename: Optional[str] = None
    ) -> str:
        """
        Download a thumbnail for a YouTube video
        
        Args:
            video_url: YouTube video URL
            output_path: Directory to save the thumbnail
            quality: Thumbnail quality (maxres, high, medium, standard, default)
            filename: Optional custom filename (without extension)
            
        Returns:
            Path to the downloaded thumbnail
            
        Raises:
            DownloadError: If download fails
        """
        logger.info(f"Downloading {quality} thumbnail for: {video_url}")
        
        try:
            # Get thumbnail URLs
            thumbnail_urls = self.get_thumbnail_urls(video_url)
            
            # Select the requested quality or fall back to the best available
            if quality not in thumbnail_urls:
                quality = "high"  # Default fallback
                
            thumbnail_url = thumbnail_urls[quality]
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Get filename
            if not filename:
                if self.api_extractor:
                    video_info = self.api_extractor.extract_video_info(video_url)
                    video_title = video_info.get("title", "thumbnail")
                    filename = safe_filename(f"{video_title}")
                else:
                    filename = "thumbnail"
                    
            # Add quality and extension to filename
            output_file = os.path.join(output_path, f"{filename}_{quality}.jpg")
            
            # Download the thumbnail
            response = self.session.get(thumbnail_url, stream=True, timeout=30)
            
            if response.status_code != 200:
                # Try other qualities if the requested one fails
                for fallback_quality in ["high", "medium", "default"]:
                    if fallback_quality != quality and fallback_quality in thumbnail_urls:
                        logger.info(f"Trying fallback quality: {fallback_quality}")
                        fallback_url = thumbnail_urls[fallback_quality]
                        response = self.session.get(fallback_url, stream=True, timeout=30)
                        if response.status_code == 200:
                            # Update output filename with new quality
                            output_file = os.path.join(output_path, f"{filename}_{fallback_quality}.jpg")
                            break
                
                if response.status_code != 200:
                    raise DownloadError(f"Failed to download thumbnail: HTTP {response.status_code}")
            
            # Save the thumbnail
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Thumbnail downloaded to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {str(e)}")
            raise DownloadError(f"Failed to download thumbnail: {str(e)}")
            
    def download_all_thumbnails(
        self,
        video_url: str,
        output_path: str = ".",
        filename: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Download all available thumbnail qualities for a video
        
        Args:
            video_url: YouTube video URL
            output_path: Directory to save the thumbnails
            filename: Optional custom filename (without extension)
            
        Returns:
            Dictionary mapping quality to downloaded file paths
        """
        logger.info(f"Downloading all thumbnail qualities for: {video_url}")
        
        try:
            # Get thumbnail URLs
            thumbnail_urls = self.get_thumbnail_urls(video_url)
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Get filename
            if not filename:
                if self.api_extractor:
                    video_info = self.api_extractor.extract_video_info(video_url)
                    video_title = video_info.get("title", "thumbnail")
                    filename = safe_filename(f"{video_title}")
                else:
                    filename = "thumbnail"
            
            # Download each thumbnail quality
            downloaded_files = {}
            
            for quality, url in thumbnail_urls.items():
                output_file = os.path.join(output_path, f"{filename}_{quality}.jpg")
                
                try:
                    response = self.session.get(url, stream=True, timeout=30)
                    
                    if response.status_code == 200:
                        with open(output_file, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                                
                        downloaded_files[quality] = output_file
                        logger.info(f"{quality} thumbnail downloaded to: {output_file}")
                    else:
                        logger.warning(f"Failed to download {quality} thumbnail: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"Error downloading {quality} thumbnail: {str(e)}")
                    
            if not downloaded_files:
                raise DownloadError("Failed to download any thumbnails")
                
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error downloading thumbnails: {str(e)}")
            raise DownloadError(f"Failed to download thumbnails: {str(e)}")