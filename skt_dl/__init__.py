"""
skt-dl - A custom YouTube video and playlist downloader

A lightweight, pure Python library for downloading YouTube videos
without external dependencies.
"""

__version__ = '0.1.0'

from .extractor import YouTubeExtractor
from .downloader import VideoDownloader
from .exceptions import (
    ExtractionError,
    DownloadError,
    RateLimitError,
    VideoUnavailableError,
    PlaylistUnavailableError
)

__all__ = [
    'YouTubeExtractor',
    'VideoDownloader',
    'ExtractionError',
    'DownloadError',
    'RateLimitError',
    'VideoUnavailableError',
    'PlaylistUnavailableError'
]
