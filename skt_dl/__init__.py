"""
skt-dl - A custom YouTube video and playlist downloader

A lightweight, pure Python library for downloading YouTube videos
without external dependencies.
"""

__version__ = '0.1.0'

from .extractor import YouTubeExtractor
from .api_extractor import YouTubeAPIExtractor
from .downloader import VideoDownloader
from .search import YouTubeSearch
from .exceptions import (
    ExtractionError,
    DownloadError,
    RateLimitError,
    VideoUnavailableError,
    PlaylistUnavailableError
)

__all__ = [
    'YouTubeExtractor',
    'YouTubeAPIExtractor',
    'VideoDownloader',
    'YouTubeSearch',
    'ExtractionError',
    'DownloadError',
    'RateLimitError',
    'VideoUnavailableError',
    'PlaylistUnavailableError'
]
