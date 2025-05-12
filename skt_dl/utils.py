"""
Utility functions for the skt-dl package
"""

import os
import re
import time
import logging
import urllib.parse
from typing import Dict, Optional, Tuple, Union, List, Callable
import json

from .constants import REGEX_PATTERNS, RATE_LIMIT_INITIAL_DELAY, MAX_RATE_LIMIT_RETRIES
from .exceptions import RateLimitError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('skt-dl')


def extract_video_id(url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID string
        
    Raises:
        ValueError: If the video ID cannot be extracted
    """
    match = re.search(REGEX_PATTERNS["video_id"], url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    return match.group(1)


def extract_json_from_html(html: str, pattern_key: str) -> Dict:
    """
    Extract and parse JSON data from HTML content using a regex pattern.
    
    Args:
        html: HTML content as string
        pattern_key: Key of the regex pattern to use from REGEX_PATTERNS
        
    Returns:
        Parsed JSON data as dict
        
    Raises:
        ValueError: If JSON data could not be extracted or parsed
    """
    pattern = REGEX_PATTERNS[pattern_key]
    match = re.search(pattern, html)
    if not match:
        raise ValueError(f"Could not extract JSON data using pattern '{pattern_key}'")
    
    json_str = match.group(1)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON data: {e}")


def safe_filename(title: str) -> str:
    """
    Convert a string to a safe filename by removing/replacing 
    special characters.
    
    Args:
        title: String to convert to a safe filename
        
    Returns:
        Safe filename string
    """
    # Replace characters that are not allowed in filenames
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    # Replace multiple spaces with a single space
    safe_title = re.sub(r'\s+', ' ', safe_title).strip()
    # Limit length to avoid file system issues
    return safe_title[:100]


def format_filesize(bytes_: int) -> str:
    """
    Format a file size in bytes to a human-readable string.
    
    Args:
        bytes_: File size in bytes
        
    Returns:
        Human-readable file size string
    """
    size_float = float(bytes_)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_float < 1024 or unit == 'TB':
            if unit == 'B':
                return f"{int(size_float)} {unit}"
            return f"{size_float:.2f} {unit}"
        size_float /= 1024
    
    # Fallback return for type checking (should never reach here)
    return f"{bytes_} B"


def calculate_eta(start_time: float, downloaded: int, total: int) -> str:
    """
    Calculate estimated time of arrival (ETA) for a download.
    
    Args:
        start_time: Time when download started (as returned by time.time())
        downloaded: Number of bytes downloaded so far
        total: Total number of bytes to download
        
    Returns:
        ETA as a formatted string
    """
    if downloaded == 0:
        return "calculating..."
    
    elapsed = time.time() - start_time
    rate = downloaded / elapsed
    if rate == 0:
        return "unknown"
    
    eta_seconds = (total - downloaded) / rate
    
    if eta_seconds < 60:
        return f"{eta_seconds:.0f}s"
    elif eta_seconds < 3600:
        return f"{eta_seconds/60:.1f}m"
    else:
        return f"{eta_seconds/3600:.1f}h"


def retry_on_rate_limit(func: Callable) -> Callable:
    """
    Decorator that retries a function if a RateLimitError is raised,
    using exponential backoff.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        retries = 0
        delay = RATE_LIMIT_INITIAL_DELAY
        
        while retries <= MAX_RATE_LIMIT_RETRIES:
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                retries += 1
                if retries > MAX_RATE_LIMIT_RETRIES:
                    raise e
                
                logger.warning(f"Rate limited. Retrying in {delay} seconds... (Attempt {retries}/{MAX_RATE_LIMIT_RETRIES})")
                time.sleep(delay)
                # Exponential backoff with jitter
                delay = delay * 2 + (time.time() % 1)
        
    return wrapper


def parse_playlist_id(url: str) -> str:
    """
    Extract the playlist ID from a YouTube playlist URL.
    
    Args:
        url: YouTube playlist URL
        
    Returns:
        Playlist ID string
        
    Raises:
        ValueError: If the playlist ID cannot be extracted
    """
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    if 'list' not in query_params:
        raise ValueError(f"Could not extract playlist ID from URL: {url}")
    
    return query_params['list'][0]


def get_terminal_size() -> Tuple[int, int]:
    """
    Get the terminal size for better progress bars
    
    Returns:
        Tuple of (columns, lines)
    """
    try:
        import shutil
        return shutil.get_terminal_size()
    except (ImportError, AttributeError):
        try:
            import os
            size = os.get_terminal_size()
            return (size.columns, size.lines)
        except (ImportError, AttributeError):
            pass
    return (80, 24)  # Default fallback size

def create_progress_bar(current: int, total: int, width: int = 0) -> str:
    """
    Create a text-based progress bar.
    
    Args:
        current: Current progress
        total: Total value
        width: Width of the progress bar in characters. If 0, auto-detect terminal width.
        
    Returns:
        Progress bar as a string
    """
    if width <= 0:
        # Auto-detect terminal width and use 2/3 of it for the progress bar
        term_width, _ = get_terminal_size()
        width = max(20, int(term_width * 2 / 3))
    
    if total == 0:
        progress = 1.0
    else:
        progress = current / total
    
    filled_width = int(width * progress)
    bar = '█' * filled_width + '░' * (width - filled_width)
    percent = progress * 100
    
    return f"[{bar}] {percent:.1f}%"
