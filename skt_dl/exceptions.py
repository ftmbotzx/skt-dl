"""
Custom exceptions for the skt-dl package
"""

class ExtractionError(Exception):
    """
    Base exception for errors that occur during video metadata extraction
    """
    pass


class DownloadError(Exception):
    """
    Base exception for errors that occur during video download
    """
    pass


class RateLimitError(Exception):
    """
    Exception raised when YouTube rate limits the requests
    """
    pass


class VideoUnavailableError(ExtractionError):
    """
    Exception raised when a video is unavailable
    (e.g., private, deleted, or region-blocked)
    """
    pass


class PlaylistUnavailableError(ExtractionError):
    """
    Exception raised when a playlist is unavailable
    """
    pass


class UnsupportedStreamError(ExtractionError):
    """
    Exception raised when a stream format is not supported
    """
    pass
