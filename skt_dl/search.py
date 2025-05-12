"""
YouTube search module for skt-dl
Uses the YouTube Data API v3 for searching videos, channels and playlists
"""

import os
import logging
from typing import Dict, List, Optional, Literal, Union, Any

import requests

from .exceptions import (
    ExtractionError,
    RateLimitError
)
from .utils import retry_on_rate_limit

logger = logging.getLogger('skt-dl.search')

class YouTubeSearch:
    """
    Class for searching YouTube videos, channels, and playlists
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the YouTube search API
        
        Args:
            api_key: YouTube Data API v3 key (defaults to YOUTUBE_API_KEY environment variable)
        """
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key not provided and YOUTUBE_API_KEY environment variable not set")
            
        self.session = requests.Session()
        self.api_base_url = "https://www.googleapis.com/youtube/v3"
    
    @retry_on_rate_limit
    def _make_api_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Make a request to the YouTube API
        
        Args:
            endpoint: API endpoint (e.g., 'search', 'videos')
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
    
    def search(
        self, 
        query: str, 
        max_results: int = 25, 
        order: Literal["date", "rating", "relevance", "title", "videoCount", "viewCount"] = "relevance",
        type_filter: Literal["video", "channel", "playlist", "all"] = "video", 
        duration: Optional[Literal["short", "medium", "long"]] = None,
        language: Optional[str] = None,
        region_code: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for YouTube videos, channels or playlists
        
        Args:
            query: Search query
            max_results: Maximum number of results to return (1-50)
            order: Order to sort results
            type_filter: Type of results to return
            duration: Filter by video duration ("short" < 4 min, "medium" 4-20 min, "long" > 20 min)
            language: Filter by language (ISO 639-1 two-letter language code)
            region_code: Filter by region (ISO 3166-1 alpha-2 country code)
            page_token: Token for pagination
            
        Returns:
            Dictionary with search results and pagination info
        """
        logger.info(f"Searching YouTube for: {query}")
        
        # Validate inputs
        if max_results < 1 or max_results > 50:
            raise ValueError("max_results must be between 1 and 50")
        
        # Set up search parameters
        params = {
            'part': 'snippet',
            'maxResults': max_results,
            'q': query,
            'order': order,
        }
        
        # Add type filter (except for 'all')
        if type_filter != 'all':
            params['type'] = type_filter
        
        # Add optional parameters
        if page_token:
            params['pageToken'] = page_token
            
        if language:
            params['relevanceLanguage'] = language
            
        if region_code:
            params['regionCode'] = region_code
            
        # Add video duration filter if needed
        if type_filter == 'video' and duration:
            params['videoDuration'] = duration
            
        # Make the API request
        search_data = self._make_api_request('search', params)
        
        # Process and return search results
        items = search_data.get('items', [])
        processed_items = []
        
        for item in items:
            kind = item.get('id', {}).get('kind', '')
            
            # Process based on item type
            if 'video' in kind:
                processed_item = self._process_video_item(item)
            elif 'channel' in kind:
                processed_item = self._process_channel_item(item)
            elif 'playlist' in kind:
                processed_item = self._process_playlist_item(item)
            else:
                # Skip unknown types
                continue
                
            processed_items.append(processed_item)
        
        # Return results with pagination tokens
        return {
            'items': processed_items,
            'next_page_token': search_data.get('nextPageToken'),
            'prev_page_token': search_data.get('prevPageToken'),
            'total_results': search_data.get('pageInfo', {}).get('totalResults', 0),
            'results_per_page': search_data.get('pageInfo', {}).get('resultsPerPage', 0)
        }
    
    def _process_video_item(self, item: Dict) -> Dict:
        """Process a video search result item"""
        snippet = item.get('snippet', {})
        video_id = item.get('id', {}).get('videoId', '')
        
        return {
            'id': video_id,
            'type': 'video',
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'thumbnail': self._get_best_thumbnail(snippet.get('thumbnails', {})),
            'channel_title': snippet.get('channelTitle', ''),
            'channel_id': snippet.get('channelId', ''),
            'published_at': snippet.get('publishedAt', ''),
            'url': f"https://www.youtube.com/watch?v={video_id}"
        }
    
    def _process_channel_item(self, item: Dict) -> Dict:
        """Process a channel search result item"""
        snippet = item.get('snippet', {})
        channel_id = item.get('id', {}).get('channelId', '')
        
        return {
            'id': channel_id,
            'type': 'channel',
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'thumbnail': self._get_best_thumbnail(snippet.get('thumbnails', {})),
            'published_at': snippet.get('publishedAt', ''),
            'url': f"https://www.youtube.com/channel/{channel_id}"
        }
    
    def _process_playlist_item(self, item: Dict) -> Dict:
        """Process a playlist search result item"""
        snippet = item.get('snippet', {})
        playlist_id = item.get('id', {}).get('playlistId', '')
        
        return {
            'id': playlist_id,
            'type': 'playlist',
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'thumbnail': self._get_best_thumbnail(snippet.get('thumbnails', {})),
            'channel_title': snippet.get('channelTitle', ''),
            'channel_id': snippet.get('channelId', ''),
            'published_at': snippet.get('publishedAt', ''),
            'url': f"https://www.youtube.com/playlist?list={playlist_id}"
        }
    
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
    
    def search_videos(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for YouTube videos
        
        Args:
            query: Search query
            **kwargs: Additional arguments to pass to search()
            
        Returns:
            Dictionary with search results
        """
        kwargs['type_filter'] = 'video'
        return self.search(query, **kwargs)
    
    def search_channels(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for YouTube channels
        
        Args:
            query: Search query
            **kwargs: Additional arguments to pass to search()
            
        Returns:
            Dictionary with search results
        """
        kwargs['type_filter'] = 'channel'
        return self.search(query, **kwargs)
    
    def search_playlists(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for YouTube playlists
        
        Args:
            query: Search query
            **kwargs: Additional arguments to pass to search()
            
        Returns:
            Dictionary with search results
        """
        kwargs['type_filter'] = 'playlist'
        return self.search(query, **kwargs)
    
    def get_video_details(self, video_ids: Union[str, List[str]]) -> List[Dict]:
        """
        Get detailed information for one or more videos
        
        Args:
            video_ids: Single video ID or list of video IDs
            
        Returns:
            List of video detail dictionaries
        """
        if isinstance(video_ids, str):
            video_ids = [video_ids]
            
        # YouTube API supports up to 50 IDs per request
        if len(video_ids) > 50:
            raise ValueError("Maximum 50 video IDs allowed per request")
            
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': ','.join(video_ids)
        }
        
        # Make the API request
        video_data = self._make_api_request('videos', params)
        
        # Process and return video details
        detailed_videos = []
        
        for item in video_data.get('items', []):
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            video_details = {
                'id': item.get('id', ''),
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'thumbnail': self._get_best_thumbnail(snippet.get('thumbnails', {})),
                'channel_title': snippet.get('channelTitle', ''),
                'channel_id': snippet.get('channelId', ''),
                'published_at': snippet.get('publishedAt', ''),
                'duration': content_details.get('duration', ''),
                'dimension': content_details.get('dimension', ''),
                'definition': content_details.get('definition', ''),
                'caption': content_details.get('caption', 'false') == 'true',
                'views': int(statistics.get('viewCount', 0)),
                'likes': int(statistics.get('likeCount', 0)),
                'favorites': int(statistics.get('favoriteCount', 0)),
                'comments': int(statistics.get('commentCount', 0)),
                'tags': snippet.get('tags', []),
                'url': f"https://www.youtube.com/watch?v={item.get('id', '')}"
            }
            
            detailed_videos.append(video_details)
            
        return detailed_videos