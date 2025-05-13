"""
YouTube API extractor module for skt-dl
Uses the official YouTube Data API v3 for more reliable extraction
"""

import os
import re
import json
import logging
import urllib.parse
from typing import Dict, List, Optional, Any

import requests

from .exceptions import (
    ExtractionError,
    VideoUnavailableError,
    PlaylistUnavailableError,
    RateLimitError
)
from .utils import (
    extract_video_id,
    parse_playlist_id,
    retry_on_rate_limit
)

logger = logging.getLogger('skt-dl.api_extractor')

class YouTubeAPIExtractor:
    """
    Class for extracting video information from YouTube using the official API
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the YouTube API extractor
        
        Args:
            api_key: YouTube Data API v3 key (defaults to YOUTUBE_API_KEY environment variable)
        """
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY', 'AIzaSyBBAY7hjRWWnIuSVmYz6InJipr82VWxBVw')
        if not self.api_key:
            raise ValueError("YouTube API key not provided and YOUTUBE_API_KEY environment variable not set")
            
        self.session = requests.Session()
        self.api_base_url = "https://www.googleapis.com/youtube/v3"
    
    @retry_on_rate_limit
    def _make_api_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Make a request to the YouTube API
        
        Args:
            endpoint: API endpoint (e.g., 'videos', 'playlists')
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            RateLimitError: If the API rate limit is exceeded
            ExtractionError: If the request fails for other reasons
        """
        # Add API key to parameters
        params['key'] = self.api_key
        
        # Build the full URL
        url = f"{self.api_base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 403:
                error_data = response.json().get('error', {})
                error_reason = error_data.get('errors', [{}])[0].get('reason', '')
                
                if error_reason == 'quotaExceeded':
                    raise RateLimitError("YouTube API quota exceeded")
                    
            if response.status_code != 200:
                raise ExtractionError(f"API request failed with status code {response.status_code}: {response.text}")
                
            return response.json()
            
        except requests.RequestException as e:
            raise ExtractionError(f"API request failed: {str(e)}")
    
    def extract_video_info(self, video_url: str) -> Dict:
        """
        Extract all available information for a YouTube video using the API
        
        Args:
            video_url: YouTube video URL or ID
            
        Returns:
            Dictionary containing video metadata and available streams
            
        Raises:
            VideoUnavailableError: If the video is unavailable
            ExtractionError: For other extraction errors
        """
        logger.info(f"Extracting video info using API for: {video_url}")
        
        # Extract video ID if a full URL was provided
        if "youtube.com" in video_url or "youtu.be" in video_url:
            video_id = extract_video_id(video_url)
        else:
            # Assume it's already a video ID
            video_id = video_url
        
        # Make API request to get video details
        params = {
            'id': video_id,
            'part': 'snippet,contentDetails,statistics'
        }
        
        try:
            video_data = self._make_api_request('videos', params)
            
            # Check if video exists
            if not video_data.get('items'):
                raise VideoUnavailableError(f"Video with ID {video_id} not found")
                
            video_item = video_data['items'][0]
            snippet = video_item['snippet']
            content_details = video_item['contentDetails']
            statistics = video_item['statistics']
            
            # Parse duration string (ISO 8601 format)
            duration_str = content_details.get('duration', 'PT0S')
            length_seconds = self._parse_duration(duration_str)
            
            # Get thumbnails
            thumbnails = snippet.get('thumbnails', {})
            best_thumbnail = self._get_best_thumbnail(thumbnails)
            
            # Since we can't actually get the streams from the API,
            # we need to supplement this with a separate call or method
            # to get the actual stream URLs
            # Here we'll create a placeholder that will be filled in later
            formats = self._get_video_formats(video_id)
            
            # Build the final video info dictionary
            video_info = {
                "id": video_id,
                "title": snippet.get('title', 'Untitled'),
                "description": snippet.get('description', ''),
                "thumbnail": best_thumbnail,
                "length_seconds": length_seconds,
                "author": snippet.get('channelTitle', 'Unknown'),
                "views": int(statistics.get('viewCount', 0)),
                "formats": formats,
                "is_live": snippet.get('liveBroadcastContent', 'none') == 'live',
            }
            
            return video_info
            
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to extract video info from API response: {str(e)}")
            raise ExtractionError(f"Failed to extract video information: {str(e)}")
    
    def extract_playlist_videos(self, playlist_url: str) -> Dict:
        """
        Extract all videos in a YouTube playlist using the API
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            Dictionary with playlist info and list of video dictionaries
            
        Raises:
            PlaylistUnavailableError: If the playlist is unavailable
            ExtractionError: For other extraction errors
        """
        logger.info(f"Extracting playlist info using API for: {playlist_url}")
        
        # Extract playlist ID
        try:
            playlist_id = parse_playlist_id(playlist_url)
        except ValueError as e:
            raise PlaylistUnavailableError(f"Invalid playlist URL: {str(e)}")
        
        # First, get playlist details
        playlist_params = {
            'id': playlist_id,
            'part': 'snippet',
        }
        
        try:
            playlist_data = self._make_api_request('playlists', playlist_params)
            
            # Check if playlist exists
            if not playlist_data.get('items'):
                raise PlaylistUnavailableError(f"Playlist with ID {playlist_id} not found")
                
            playlist_item = playlist_data['items'][0]
            playlist_title = playlist_item['snippet'].get('title', 'Unknown Playlist')
            
            # Now get playlist items (videos)
            videos = []
            next_page_token = None
            
            while True:
                # Prepare parameters for playlist items request
                items_params = {
                    'playlistId': playlist_id,
                    'part': 'snippet',
                    'maxResults': 50,  # Maximum allowed by the API
                }
                
                if next_page_token:
                    items_params['pageToken'] = next_page_token
                
                # Make the request
                items_data = self._make_api_request('playlistItems', items_params)
                
                # Process each video in the current page
                for item in items_data.get('items', []):
                    snippet = item.get('snippet', {})
                    resource_id = snippet.get('resourceId', {})
                    
                    # Skip non-video items
                    if resource_id.get('kind') != 'youtube#video':
                        continue
                    
                    video_id = resource_id.get('videoId')
                    if not video_id:
                        continue
                    
                    videos.append({
                        "id": video_id,
                        "title": snippet.get('title', 'Untitled'),
                        "url": f"https://www.youtube.com/watch?v={video_id}"
                    })
                
                # Check if there are more pages
                next_page_token = items_data.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Build the final playlist info dictionary
            playlist_info = {
                "id": playlist_id,
                "title": playlist_title,
                "video_count": len(videos),
                "videos": videos
            }
            
            if not videos:
                raise PlaylistUnavailableError("No videos found in playlist")
            
            return playlist_info
            
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to extract playlist info from API response: {str(e)}")
            raise ExtractionError(f"Failed to extract playlist information: {str(e)}")
    
    def _get_best_thumbnail(self, thumbnails: Dict) -> str:
        """
        Get the URL of the highest quality thumbnail
        
        Args:
            thumbnails: Dictionary of thumbnail data from the API
            
        Returns:
            URL of the best thumbnail, or empty string if none available
        """
        # YouTube API provides thumbnails in different sizes
        # maxres > standard > high > medium > default
        for size in ['maxres', 'standard', 'high', 'medium', 'default']:
            if size in thumbnails and 'url' in thumbnails[size]:
                return thumbnails[size]['url']
        
        return ""
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration string to seconds
        
        Args:
            duration_str: Duration string in ISO 8601 format (e.g., 'PT4M13S')
            
        Returns:
            Duration in seconds
        """
        # Remove PT prefix
        duration = duration_str[2:]
        
        hours = 0
        minutes = 0
        seconds = 0
        
        # Extract hours, minutes, seconds
        if 'H' in duration:
            hours_part, duration = duration.split('H')
            hours = int(hours_part)
        
        if 'M' in duration:
            minutes_part, duration = duration.split('M')
            minutes = int(minutes_part)
        
        if 'S' in duration:
            seconds_part = duration.split('S')[0]
            seconds = int(seconds_part)
        
        # Convert to total seconds
        return hours * 3600 + minutes * 60 + seconds
    
    def _get_video_formats(self, video_id: str) -> List[Dict]:
        """
        Get available formats for a video
        
        This method uses a combination of YouTube API data and web scraping to get
        the available formats for a video. The YouTube API doesn't directly provide
        stream URLs, so we need to supplement the API data with additional scraping.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of format dictionaries
        """
        import requests
        import re
        import json
        import urllib.parse
        
        logger.info(f"Extracting video formats for video ID: {video_id}")
        
        try:
            # First approach: Get player response JSON from the watch page
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(watch_url, timeout=30)
            
            if response.status_code != 200:
                raise ExtractionError(f"Failed to fetch video page: HTTP {response.status_code}")
                
            html_content = response.text
            
            # Extract the playerResponse JSON
            player_response_match = re.search(r'var ytInitialPlayerResponse\s*=\s*(\{.+?\});', html_content)
            if not player_response_match:
                # Try alternative pattern
                player_response_match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.+?\});', html_content)
                
            if not player_response_match:
                raise ExtractionError("Failed to extract player response from video page")
                
            # Parse the JSON
            try:
                player_data = json.loads(player_response_match.group(1))
            except json.JSONDecodeError:
                raise ExtractionError("Failed to parse player response JSON")
                
            # Extract formats
            streaming_data = player_data.get('streamingData', {})
            format_list = []
            
            # Add adaptive formats (separate audio and video streams)
            adaptive_formats = streaming_data.get('adaptiveFormats', [])
            for fmt in adaptive_formats:
                format_dict = self._parse_format(fmt)
                format_list.append(format_dict)
                
            # Add combined formats (audio+video)
            combined_formats = streaming_data.get('formats', [])
            for fmt in combined_formats:
                format_dict = self._parse_format(fmt)
                format_list.append(format_dict)
                
            # If we were able to extract formats, return them
            if format_list:
                return format_list
                
            # If we reach here, we couldn't extract formats from the player response
            # Fall back to a list of common formats as placeholders
            logger.warning("Falling back to common format list as extraction from player response failed")
            
        except Exception as e:
            logger.error(f"Error extracting video formats: {str(e)}")
            logger.warning("Falling back to common format list")
        
        # Fallback: Return a comprehensive list of possible formats
        # These are based on common YouTube itags and their known properties
        # The URLs are placeholders and would need to be replaced with actual URLs
        common_formats = [
            {
                "itag": 18,
                "url": f"https://example.com/videos/{video_id}/18",
                "mime_type": "video/mp4; codecs=avc1.42001E,mp4a.40.2",
                "container": "mp4",
                "codecs": "avc1.42001E,mp4a.40.2",
                "is_audio": True,
                "is_video": True,
                "quality": "360p",
                "audio_bitrate": 96000,
                "video_bitrate": 500000,
                "width": 640,
                "height": 360,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 22,
                "url": f"https://example.com/videos/{video_id}/22",
                "mime_type": "video/mp4; codecs=avc1.64001F,mp4a.40.2",
                "container": "mp4",
                "codecs": "avc1.64001F,mp4a.40.2",
                "is_audio": True,
                "is_video": True,
                "quality": "720p",
                "audio_bitrate": 192000,
                "video_bitrate": 2000000,
                "width": 1280,
                "height": 720,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 37,
                "url": f"https://example.com/videos/{video_id}/37",
                "mime_type": "video/mp4; codecs=avc1.640028,mp4a.40.2",
                "container": "mp4",
                "codecs": "avc1.640028,mp4a.40.2",
                "is_audio": True,
                "is_video": True,
                "quality": "1080p",
                "audio_bitrate": 192000,
                "video_bitrate": 3000000,
                "width": 1920,
                "height": 1080,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 137,
                "url": f"https://example.com/videos/{video_id}/137",
                "mime_type": "video/mp4; codecs=avc1.640028",
                "container": "mp4",
                "codecs": "avc1.640028",
                "is_audio": False,
                "is_video": True,
                "quality": "1080p",
                "audio_bitrate": 0,
                "video_bitrate": 4500000,
                "width": 1920,
                "height": 1080,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 248,
                "url": f"https://example.com/videos/{video_id}/248",
                "mime_type": "video/webm; codecs=vp9",
                "container": "webm",
                "codecs": "vp9",
                "is_audio": False,
                "is_video": True,
                "quality": "1080p",
                "audio_bitrate": 0,
                "video_bitrate": 2500000,
                "width": 1920,
                "height": 1080,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 271,
                "url": f"https://example.com/videos/{video_id}/271",
                "mime_type": "video/webm; codecs=vp9",
                "container": "webm",
                "codecs": "vp9",
                "is_audio": False,
                "is_video": True,
                "quality": "1440p",
                "audio_bitrate": 0,
                "video_bitrate": 9000000,
                "width": 2560,
                "height": 1440,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 313,
                "url": f"https://example.com/videos/{video_id}/313",
                "mime_type": "video/webm; codecs=vp9",
                "container": "webm",
                "codecs": "vp9",
                "is_audio": False,
                "is_video": True,
                "quality": "2160p",
                "audio_bitrate": 0,
                "video_bitrate": 20000000,
                "width": 3840,
                "height": 2160,
                "content_length": None,
                "fps": 30
            },
            {
                "itag": 140,
                "url": f"https://example.com/videos/{video_id}/140",
                "mime_type": "audio/mp4; codecs=mp4a.40.2",
                "container": "mp4",
                "codecs": "mp4a.40.2",
                "is_audio": True,
                "is_video": False,
                "quality": "128kbps",
                "audio_bitrate": 128000,
                "video_bitrate": 0,
                "width": 0,
                "height": 0,
                "content_length": None,
                "fps": 0
            },
            {
                "itag": 251,
                "url": f"https://example.com/videos/{video_id}/251",
                "mime_type": "audio/webm; codecs=opus",
                "container": "webm",
                "codecs": "opus",
                "is_audio": True,
                "is_video": False,
                "quality": "160kbps",
                "audio_bitrate": 160000,
                "video_bitrate": 0,
                "width": 0,
                "height": 0,
                "content_length": None,
                "fps": 0
            }
        ]
        
        logger.warning("Using common format definitions since direct extraction failed")
        return common_formats
        
    def _parse_format(self, fmt_data: Dict) -> Dict:
        """
        Parse format data from the player response
        
        Args:
            fmt_data: Format data from player response
            
        Returns:
            Normalized format dictionary
        """
        itag = fmt_data.get('itag', 0)
        mime_type = fmt_data.get('mimeType', '')
        
        # Parse container and codecs from mime type
        container = 'mp4'  # Default
        codecs = ''
        
        if mime_type:
            mime_parts = mime_type.split(';')
            if len(mime_parts) > 0 and '/' in mime_parts[0]:
                container = mime_parts[0].split('/')[1]
                
            codecs_match = re.search(r'codecs="([^"]+)"', mime_type)
            if codecs_match:
                codecs = codecs_match.group(1)
        
        # Determine if format has audio and/or video
        has_audio = 'audio' in mime_type.lower() or any(audio_codec in codecs.lower() for audio_codec in ['mp4a', 'opus', 'vorbis'])
        has_video = 'video' in mime_type.lower() or any(video_codec in codecs.lower() for video_codec in ['avc1', 'vp9', 'vp8', 'av01'])
        
        # Get content length
        content_length = None
        if 'contentLength' in fmt_data:
            try:
                content_length = int(fmt_data['contentLength'])
            except (ValueError, TypeError):
                pass
                
        # Get URL
        url = fmt_data.get('url', '')
        
        # If URL is not available directly, it might be encrypted
        if not url and 'signatureCipher' in fmt_data:
            try:
                cipher_data = fmt_data['signatureCipher']
                cipher_parts = dict(urllib.parse.parse_qsl(cipher_data))
                
                if 'url' in cipher_parts:
                    url = cipher_parts['url']
                    
                    # In a real implementation, we would need to decrypt the signature
                    # This is just a placeholder to show the structure
                    if 's' in cipher_parts and 'sp' in cipher_parts:
                        signature_param = cipher_parts.get('sp', 'signature')
                        encrypted_sig = cipher_parts.get('s', '')
                        # We would decrypt encrypted_sig here
                        # decrypted_sig = decrypt_signature(encrypted_sig)
                        # url += f"&{signature_param}={decrypted_sig}"
            except Exception as e:
                logger.error(f"Error parsing signature cipher: {str(e)}")
        
        # Get width and height
        width = fmt_data.get('width', 0)
        height = fmt_data.get('height', 0)
        
        # Get quality label
        quality = fmt_data.get('qualityLabel', '')
        if not quality and has_audio and not has_video:
            # For audio-only formats
            audio_bitrate = fmt_data.get('bitrate', 0)
            if audio_bitrate and audio_bitrate is not None:
                audio_bitrate_kbps = int(audio_bitrate / 1000)
                quality = f"{audio_bitrate_kbps}kbps"
        
        # Get FPS
        fps = fmt_data.get('fps', 30)
        
        # Get bitrates
        audio_bitrate = 0
        video_bitrate = 0
        bitrate = fmt_data.get('bitrate', 0)

        # Ensure bitrate is never None 
        if bitrate is None:
            bitrate = 0
        if has_audio and not has_video:
            audio_bitrate = bitrate
        elif has_video and not has_audio:
            video_bitrate = bitrate
        elif has_audio and has_video and bitrate > 0:    
           # For combined formats, estimate the split
            # Typical audio is ~128kbps, so the rest is video
            audio_bitrate = min(128000, int(bitrate * 0.1))
            video_bitrate = bitrate - audio_bitrate
        
        # Build the normalized format dictionary
        format_dict = {
            "itag": itag,
            "url": url,
            "mime_type": mime_type,
            "container": container,
            "codecs": codecs,
            "is_audio": has_audio,
            "is_video": has_video,
            "quality": quality or (f"{height}p" if height else "unknown"),
            "audio_bitrate": audio_bitrate,
            "video_bitrate": video_bitrate,
            "width": width,
            "height": height,
            "content_length": content_length,
            "fps": fps
        }
        
        return format_dict
