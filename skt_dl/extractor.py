"""
Core YouTube extraction functionality to parse video and playlist data
"""

import re
import json
import time
import logging
import urllib.parse
from typing import Dict, List, Tuple, Optional, Union, Any

import requests

from .constants import (
    DEFAULT_HEADERS,
    YOUTUBE_WATCH_URL,
    YOUTUBE_PLAYLIST_URL,
    REGEX_PATTERNS,
)
from .exceptions import (
    ExtractionError,
    VideoUnavailableError,
    PlaylistUnavailableError,
    RateLimitError,
)
from .utils import (
    extract_video_id,
    extract_json_from_html,
    parse_playlist_id,
    retry_on_rate_limit,
)

logger = logging.getLogger('skt-dl.extractor')


class YouTubeExtractor:
    """
    Class for extracting video information from YouTube
    """
    
    def __init__(self):
        """Initialize the YouTube extractor with a requests session"""
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
    
    @retry_on_rate_limit
    def _make_request(self, url: str, params: Optional[Dict] = None) -> str:
        """
        Make an HTTP request with rate limit handling
        
        Args:
            url: URL to request
            params: Optional URL parameters
            
        Returns:
            Response text
            
        Raises:
            RateLimitError: If the request is rate-limited
            ExtractionError: If the request fails for other reasons
        """
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                raise RateLimitError("YouTube rate limit exceeded")
                
            if response.status_code != 200:
                raise ExtractionError(f"Request failed with status code {response.status_code}")
                
            return response.text
            
        except requests.RequestException as e:
            raise ExtractionError(f"Request failed: {str(e)}")
    
    def extract_video_info(self, video_url: str) -> Dict:
        """
        Extract all available information for a YouTube video
        
        Args:
            video_url: YouTube video URL or ID
            
        Returns:
            Dictionary containing video metadata and available streams
            
        Raises:
            VideoUnavailableError: If the video is unavailable
            ExtractionError: For other extraction errors
        """
        logger.info(f"Extracting video info for: {video_url}")
        
        # Extract video ID if a full URL was provided
        if "youtube.com" in video_url or "youtu.be" in video_url:
            video_id = extract_video_id(video_url)
        else:
            # Assume it's already a video ID
            video_id = video_url
        
        # Make request to video page
        html = self._make_request(YOUTUBE_WATCH_URL, params={"v": video_id})
        
        try:
            # Extract player response data
            player_response = extract_json_from_html(html, "player_response")
            
            # Check if video is playable
            playability_status = player_response.get("playabilityStatus", {})
            if playability_status.get("status") != "OK":
                reason = playability_status.get("reason", "Unknown reason")
                raise VideoUnavailableError(f"Video unavailable: {reason}")
            
            # Extract basic video details
            video_details = player_response.get("videoDetails", {})
            streaming_data = player_response.get("streamingData", {})
            
            # Extract formats
            formats = []
            
            # Add adaptive formats (separate audio and video)
            if "adaptiveFormats" in streaming_data:
                formats.extend(streaming_data["adaptiveFormats"])
                
            # Add combined formats (audio and video together)
            if "formats" in streaming_data:
                formats.extend(streaming_data["formats"])
            
            # Process and normalize format information
            processed_formats = self._process_formats(formats)
            
            # Build the final video info dictionary
            video_info = {
                "id": video_id,
                "title": video_details.get("title", "Untitled"),
                "description": video_details.get("shortDescription", ""),
                "thumbnail": self._get_best_thumbnail(video_details.get("thumbnail", {}).get("thumbnails", [])),
                "length_seconds": int(video_details.get("lengthSeconds", 0)),
                "author": video_details.get("author", "Unknown"),
                "views": int(video_details.get("viewCount", 0)),
                "formats": processed_formats,
                "is_live": video_details.get("isLiveContent", False),
            }
            
            return video_info
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to extract video info: {str(e)}")
            raise ExtractionError(f"Failed to extract video information: {str(e)}")
    
    def _process_formats(self, formats: List[Dict]) -> List[Dict]:
        """
        Process and normalize format information from YouTube
        
        Args:
            formats: List of format dictionaries from YouTube API
            
        Returns:
            Processed and normalized format list
        """
        processed = []
        
        for fmt in formats:
            # Skip formats without URLs
            if "url" not in fmt:
                continue
                
            # Get basic format information
            itag = fmt.get("itag", 0)
            mime_type = fmt.get("mimeType", "")
            
            # Parse mime type to extract codec information
            mime_info = re.search(r'(\w+\/\w+);\scodecs="([^"]+)"', mime_type)
            container = "unknown"
            codecs = "unknown"
            
            if mime_info:
                container = mime_info.group(1).split('/')[1]
                codecs = mime_info.group(2)
            
            # Determine if it's audio, video, or both
            is_audio = "audio" in mime_type
            is_video = "video" in mime_type
            
            # Get quality information
            quality = fmt.get("qualityLabel", "Unknown")
            if not quality and is_audio:
                audio_quality = fmt.get("audioQuality", "")
                if "AUDIO_QUALITY_LOW" in audio_quality:
                    quality = "Low"
                elif "AUDIO_QUALITY_MEDIUM" in audio_quality:
                    quality = "Medium"
                elif "AUDIO_QUALITY_HIGH" in audio_quality:
                    quality = "High"
                else:
                    quality = "Unknown"
            
            # Get bitrates
            audio_bitrate = fmt.get("audioBitrate", 0) if is_audio else 0
            video_bitrate = fmt.get("bitrate", 0) if is_video else 0
            
            # Get size information
            width = fmt.get("width", 0)
            height = fmt.get("height", 0)
            
            # Get content length (file size)
            content_length = int(fmt.get("contentLength", 0))
            
            # Get frame rate
            fps = fmt.get("fps", 0)
            
            processed.append({
                "itag": itag,
                "url": fmt["url"],
                "mime_type": mime_type,
                "container": container,
                "codecs": codecs,
                "is_audio": is_audio,
                "is_video": is_video,
                "quality": quality,
                "audio_bitrate": audio_bitrate,
                "video_bitrate": video_bitrate,
                "width": width,
                "height": height,
                "content_length": content_length,
                "fps": fps
            })
        
        return processed
    
    def _get_best_thumbnail(self, thumbnails: List[Dict]) -> str:
        """
        Get the URL of the highest quality thumbnail
        
        Args:
            thumbnails: List of thumbnail dictionaries
            
        Returns:
            URL of the best thumbnail, or empty string if none available
        """
        if not thumbnails:
            return ""
            
        # Sort thumbnails by width (descending)
        sorted_thumbnails = sorted(
            thumbnails, 
            key=lambda t: (t.get("width", 0), t.get("height", 0)), 
            reverse=True
        )
        
        # Return the URL of the largest thumbnail
        return sorted_thumbnails[0].get("url", "")
    
    def extract_playlist_videos(self, playlist_url: str) -> List[Dict]:
        """
        Extract all videos in a YouTube playlist
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of dictionaries with video information
            
        Raises:
            PlaylistUnavailableError: If the playlist is unavailable
            ExtractionError: For other extraction errors
        """
        logger.info(f"Extracting playlist info for: {playlist_url}")
        
        # Extract playlist ID
        try:
            playlist_id = parse_playlist_id(playlist_url)
        except ValueError as e:
            raise PlaylistUnavailableError(f"Invalid playlist URL: {str(e)}")
        
        # Make request to playlist page
        html = self._make_request(YOUTUBE_PLAYLIST_URL, params={"list": playlist_id})
        
        try:
            # Extract initial data
            initial_data = extract_json_from_html(html, "initial_data")
            
            # Extract playlist metadata
            sidebar = initial_data.get("sidebar", {}).get("playlistSidebarRenderer", {})
            sidebar_items = sidebar.get("items", [])
            
            playlist_info = {}
            
            # Extract playlist metadata from sidebar
            if sidebar_items:
                stats_item = sidebar_items[0].get("playlistSidebarPrimaryInfoRenderer", {})
                title_text = stats_item.get("title", {}).get("runs", [{}])[0].get("text", "Unknown Playlist")
                
                playlist_info = {
                    "id": playlist_id,
                    "title": title_text,
                }
            
            # Extract videos from the playlist
            videos = []
            
            # Navigate to the contents section of the response
            contents = initial_data.get("contents", {})
            tab_contents = contents.get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])[0].get("tabRenderer", {})
            section_list = tab_contents.get("content", {}).get("sectionListRenderer", {})
            
            video_items = []
            
            # Process section contents to find video items
            for section in section_list.get("contents", []):
                item_section = section.get("itemSectionRenderer", {})
                for content in item_section.get("contents", []):
                    playlist_renderer = content.get("playlistVideoListRenderer", {})
                    video_items.extend(playlist_renderer.get("contents", []))
            
            # Extract basic info for each video
            for item in video_items:
                video_renderer = item.get("playlistVideoRenderer", {})
                if not video_renderer:
                    continue
                
                video_id = video_renderer.get("videoId", "")
                if not video_id:
                    continue
                
                title = "Untitled"
                title_runs = video_renderer.get("title", {}).get("runs", [])
                if title_runs:
                    title = title_runs[0].get("text", "Untitled")
                
                videos.append({
                    "id": video_id,
                    "title": title,
                    "url": f"{YOUTUBE_WATCH_URL}?v={video_id}"
                })
            
            # Update playlist info with video count and video list
            playlist_info["video_count"] = len(videos)
            playlist_info["videos"] = videos
            
            if not videos:
                raise PlaylistUnavailableError("No videos found in playlist")
            
            return playlist_info
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to extract playlist info: {str(e)}")
            raise ExtractionError(f"Failed to extract playlist information: {str(e)}")
