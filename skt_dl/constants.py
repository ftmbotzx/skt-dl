"""
Constants used throughout the skt-dl package
"""

# User agent to use for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Default headers for HTTP requests
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# YouTube base URLs
YOUTUBE_BASE_URL = "https://www.youtube.com"
YOUTUBE_WATCH_URL = f"{YOUTUBE_BASE_URL}/watch"
YOUTUBE_PLAYLIST_URL = f"{YOUTUBE_BASE_URL}/playlist"

# Quality mappings for easy reference
QUALITY_LABELS = {
    "144p": 144,
    "240p": 240,
    "360p": 360,
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
    "1440p": 1440,
    "2160p": 2160,
}

# Buffer size for downloading (1MB)
DOWNLOAD_CHUNK_SIZE = 1024 * 1024

# Common regex patterns
REGEX_PATTERNS = {
    # Pattern to extract initial player response JSON
    "player_response": r'ytInitialPlayerResponse\s*=\s*({.*?});',
    
    # Pattern to extract initial data JSON
    "initial_data": r'ytInitialData\s*=\s*({.*?});',
    
    # Pattern to extract video id from URL
    "video_id": r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
    
    # Pattern to extract player JS URL
    "player_js": r'PLAYER_JS_URL":"(.*?)"',
    
    # Pattern to extract signature function name
    "sig_function": r'(?:a=a.split\(""\);)(.*?)\.join\(""\)'
}

# Initial delay for rate limit backoff (in seconds)
RATE_LIMIT_INITIAL_DELAY = 5

# Maximum number of retries for rate-limited requests
MAX_RATE_LIMIT_RETRIES = 5
