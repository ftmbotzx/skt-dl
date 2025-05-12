#!/usr/bin/env python3
"""
Command-line interface for skt-dl
"""

import os
import sys
import time
import logging
import argparse
from typing import Optional, Dict, Any

from . import __version__
from .api_extractor import YouTubeAPIExtractor
from .downloader import VideoDownloader, default_progress_callback
from .search import YouTubeSearch
from .captions import SubtitleDownloader
from .thumbnail import ThumbnailDownloader
from .concurrent import ConcurrentDownloader
from .exceptions import (
    ExtractionError,
    DownloadError,
    RateLimitError,
    VideoUnavailableError,
    PlaylistUnavailableError
)

logger = logging.getLogger('skt-dl.cli')

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='skt-dl',
        description='A custom YouTube video and playlist downloader',
        epilog='Example: skt-dl https://www.youtube.com/watch?v=dQw4w9WgXcQ -o downloads/ -q 720p'
    )
    
    # Version information
    parser.add_argument('-v', '--version', action='store_true', help='Show version information')
    
    # Verbose output
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a video or playlist')
    download_parser.add_argument('url', help='YouTube URL to download')
    download_parser.add_argument('-o', '--output', default='.', help='Output directory')
    download_parser.add_argument('-q', '--quality', default='best', help='Video quality to download (e.g., best, worst, 720p, 480p)')
    download_parser.add_argument('-f', '--filename', help='Custom filename (without extension)')
    download_parser.add_argument('--audio-only', action='store_true', help='Download audio only')
    download_parser.add_argument('--video-only', action='store_true', help='Download video only (no audio)')
    download_parser.add_argument('--format', choices=['mp4', 'webm'], help='Preferred format (mp4 or webm)')
    download_parser.add_argument('--list-formats', action='store_true', help='List available formats instead of downloading')
    download_parser.add_argument('--with-subtitles', action='store_true', help='Download subtitles along with the video')
    download_parser.add_argument('--subtitles-only', action='store_true', help='Download only the subtitles')
    download_parser.add_argument('--subtitle-lang', default='en', help='Language code for subtitles (e.g., en, es, fr)')
    download_parser.add_argument('--subtitle-format', choices=['srt', 'vtt', 'json', 'xml'], default='srt', help='Subtitle format')
    download_parser.add_argument('--with-thumbnail', action='store_true', help='Download thumbnail along with the video')
    download_parser.add_argument('--thumbnail-only', action='store_true', help='Download only the thumbnail')
    download_parser.add_argument('--thumbnail-quality', choices=['maxres', 'high', 'medium', 'standard', 'default'], default='high', help='Thumbnail quality')
    download_parser.add_argument('--all-thumbnails', action='store_true', help='Download all available thumbnail qualities')
    download_parser.add_argument('--concurrent', action='store_true', help='Use concurrent downloads for playlists')
    download_parser.add_argument('--max-workers', type=int, default=4, help='Maximum number of concurrent download workers (1-16)')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for YouTube videos, channels, or playlists')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-t', '--type', choices=['video', 'channel', 'playlist', 'all'], default='video', help='Type of search results to return')
    search_parser.add_argument('-n', '--max-results', type=int, default=5, help='Maximum number of results to return (1-50)')
    search_parser.add_argument('-o', '--order', choices=['date', 'rating', 'relevance', 'title', 'viewCount'], default='relevance', help='Order to sort results')
    search_parser.add_argument('-d', '--download', action='store_true', help='Download the first video from search results')
    search_parser.add_argument('-q', '--quality', default='best', help='Video quality to download if --download is specified')
    search_parser.add_argument('--output', default='.', help='Output directory for downloads')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Get information about a video or playlist')
    info_parser.add_argument('url', help='YouTube URL to get information about')
    
    # Subtitle command
    subtitle_parser = subparsers.add_parser('subtitle', help='Download video subtitles')
    subtitle_parser.add_argument('url', help='YouTube URL to download subtitles from')
    subtitle_parser.add_argument('-o', '--output', default='.', help='Output directory')
    subtitle_parser.add_argument('-f', '--filename', help='Custom filename (without extension)')
    subtitle_parser.add_argument('-l', '--language', default='en', help='Language code (e.g., en, es, fr)')
    subtitle_parser.add_argument('--format', choices=['srt', 'vtt', 'json', 'xml'], default='srt', help='Subtitle format')
    subtitle_parser.add_argument('--list', action='store_true', help='List available subtitle languages')
    
    # Thumbnail command
    thumbnail_parser = subparsers.add_parser('thumbnail', help='Download video thumbnails')
    thumbnail_parser.add_argument('url', help='YouTube URL to download thumbnail from')
    thumbnail_parser.add_argument('-o', '--output', default='.', help='Output directory')
    thumbnail_parser.add_argument('-f', '--filename', help='Custom filename (without extension)')
    thumbnail_parser.add_argument('-q', '--quality', choices=['maxres', 'high', 'medium', 'standard', 'default'], default='high', help='Thumbnail quality')
    thumbnail_parser.add_argument('--all', action='store_true', help='Download all available thumbnail qualities')
    
    args = parser.parse_args()
    
    # Default to download command if no command is specified but URL is provided
    if len(sys.argv) > 1 and not args.command and not args.version:
        if '://' in sys.argv[1] or 'youtu' in sys.argv[1]:
            args.command = 'download'
            args.url = sys.argv[1]
            args.output = '.'
            args.quality = 'best'
            args.filename = None
            args.audio_only = False
            args.video_only = False
            args.format = None
            args.list_formats = False
            
            # Check for additional args
            for i, arg in enumerate(sys.argv[2:]):
                if arg == '-o' or arg == '--output':
                    try:
                        args.output = sys.argv[i+3]
                    except IndexError:
                        pass
                elif arg == '-q' or arg == '--quality':
                    try:
                        args.quality = sys.argv[i+3]
                    except IndexError:
                        pass
                elif arg == '--audio-only':
                    args.audio_only = True
                elif arg == '--video-only':
                    args.video_only = True
                elif arg == '--list-formats':
                    args.list_formats = True
    
    return args

def configure_logging(verbose: bool) -> None:
    """
    Configure logging based on verbosity level
    
    Args:
        verbose: Whether to enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress verbose logs from requests
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def show_version() -> None:
    """
    Display version information
    """
    print(f"skt-dl version {__version__}")
    print("A custom YouTube video and playlist downloader")
    print("https://github.com/user/skt-dl")
    print("\nSupported features:")
    print("- Video downloading with quality selection")
    print("- Playlist downloading")
    print("- YouTube video/channel/playlist search")
    print("- Separate audio and video streams")
    print("- Multiple formats (mp4, webm)")
    print("- MP4, WebM containers")
    print("- H.264, VP9, AV1 video codecs")
    print("- MP3, AAC, Opus audio codecs")

def download_video(args: argparse.Namespace) -> None:
    """
    Download a single video
    
    Args:
        args: Parsed command-line arguments
    """
    # Create extractor and downloader
    try:
        extractor = YouTubeAPIExtractor()
        downloader = VideoDownloader(extractor)
        
        # Check if the URL is a video or a playlist
        if 'playlist' in args.url or 'list=' in args.url:
            download_playlist(args)
            return
            
        # If list_formats is specified, fetch video info and show available formats
        if args.list_formats:
            print(f"Fetching available formats for: {args.url}")
            video_info = extractor.extract_video_info(args.url)
            
            print(f"\nTitle: {video_info['title']}")
            print(f"Author: {video_info['author']}")
            print(f"Duration: {video_info['length_seconds']} seconds")
            
            print("\nAvailable formats:")
            print("-" * 80)
            print(f"{'ID':<6} {'Type':<10} {'Container':<10} {'Resolution':<12} {'FPS':<5} {'Codec':<15} {'Bitrate':<12}")
            print("-" * 80)
            
            # Group formats by type (audio+video, video-only, audio-only)
            av_formats = []
            video_formats = []
            audio_formats = []
            
            for fmt in video_info['formats']:
                if fmt['is_audio'] and fmt['is_video']:
                    av_formats.append(fmt)
                elif fmt['is_video']:
                    video_formats.append(fmt)
                elif fmt['is_audio']:
                    audio_formats.append(fmt)
            
            # Sort formats by quality
            def sort_key(fmt):
                if fmt['is_video']:
                    return (0 if fmt['is_audio'] else 1, -fmt['height'] if 'height' in fmt else 0)
                else:
                    return (2, -fmt['audio_bitrate'] if 'audio_bitrate' in fmt else 0)
                    
            av_formats.sort(key=sort_key)
            video_formats.sort(key=sort_key)
            audio_formats.sort(key=lambda fmt: -fmt['audio_bitrate'] if 'audio_bitrate' in fmt else 0)
            
            # Print audio+video formats
            if av_formats:
                print("\nAudio + Video Formats:")
                for fmt in av_formats:
                    print(f"{fmt['itag']:<6} {'AV':<10} {fmt['container']:<10} {fmt.get('quality', 'N/A'):<12} {fmt.get('fps', 'N/A'):<5} {fmt['codecs']:<15} {fmt.get('audio_bitrate', 0)//1000 + fmt.get('video_bitrate', 0)//1000:<7}kbps")
            
            # Print video-only formats
            if video_formats:
                print("\nVideo-Only Formats:")
                for fmt in video_formats:
                    print(f"{fmt['itag']:<6} {'Video':<10} {fmt['container']:<10} {fmt.get('quality', 'N/A'):<12} {fmt.get('fps', 'N/A'):<5} {fmt['codecs']:<15} {fmt.get('video_bitrate', 0)//1000:<7}kbps")
            
            # Print audio-only formats
            if audio_formats:
                print("\nAudio-Only Formats:")
                for fmt in audio_formats:
                    print(f"{fmt['itag']:<6} {'Audio':<10} {fmt['container']:<10} {fmt.get('quality', 'N/A'):<12} {'N/A':<5} {fmt['codecs']:<15} {fmt.get('audio_bitrate', 0)//1000:<7}kbps")
            
            print("\nTo download a specific format, use: skt-dl <url> -q itag:<itag>")
            print("Example: skt-dl https://www.youtube.com/watch?v=dQw4w9WgXcQ -q itag:22")
            return
        
        # Download the video
        print(f"Downloading video: {args.url}")
        
        # Determine quality settings based on command-line args
        quality = args.quality
        if args.audio_only:
            quality = "audio"
        elif args.video_only:
            quality = "video"
            
        if args.format:
            quality = f"{quality}:{args.format}"
            
        output_file = downloader.download_video(
            args.url,
            output_path=args.output,
            quality=quality,
            progress_callback=default_progress_callback,
            filename=args.filename
        )
        
        print(f"\nVideo downloaded successfully to: {output_file}")
        
    except VideoUnavailableError as e:
        print(f"Error: Video unavailable - {str(e)}")
        sys.exit(1)
    except (ExtractionError, DownloadError) as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDownload canceled by user")
        sys.exit(1)

def download_playlist(args: argparse.Namespace) -> None:
    """
    Download a playlist
    
    Args:
        args: Parsed command-line arguments
    """
    try:
        # Create extractor
        extractor = YouTubeAPIExtractor()
        
        # Get playlist info first
        print(f"Fetching playlist info: {args.url}")
        playlist_info = extractor.extract_playlist_videos(args.url)
        
        print(f"\nPlaylist: {playlist_info['title']}")
        print(f"Videos: {playlist_info['video_count']}")
        
        choice = input(f"Download {playlist_info['video_count']} videos? [y/N] ")
        if choice.lower() != 'y':
            print("Download canceled")
            return
        
        # Determine quality settings based on command-line args
        quality = args.quality
        if args.audio_only:
            quality = "audio"
        elif args.video_only:
            quality = "video"
            
        if args.format:
            quality = f"{quality}:{args.format}"
        
        # Check if concurrent download is enabled
        if hasattr(args, 'concurrent') and args.concurrent:
            # Use concurrent downloader
            print(f"Downloading playlist: {playlist_info['title']} (concurrent with {args.max_workers} workers)")
            
            # Validate and limit max_workers
            max_workers = min(max(1, args.max_workers), 16)
            
            # Create a concurrent downloader
            concurrent_downloader = ConcurrentDownloader(max_workers=max_workers, extractor=extractor)
            
            # Define progress callback for concurrent downloads
            def concurrent_progress_callback(
                bytes_downloaded: int,
                total_bytes: int,
                elapsed: float,
                file_index: int = 1,
                total_files: int = 1,
                current_title: str = ""
            ) -> None:
                # Call the default progress callback
                default_progress_callback(
                    bytes_downloaded,
                    total_bytes,
                    elapsed,
                    file_index,
                    total_files,
                    current_title
                )
            
            # Download the playlist concurrently
            downloaded_files, errors = concurrent_downloader.download_playlist(
                playlist_url=args.url,
                output_path=args.output,
                quality=quality,
                progress_callback=concurrent_progress_callback
            )
            
            # Print results
            print(f"\nPlaylist download completed:")
            print(f"  Downloaded: {len(downloaded_files)} videos")
            print(f"  Failed: {len(errors)} videos")
            
            if errors:
                print("\nFailed videos:")
                for error in errors:
                    print(f"  {error['index']}. {error['title']}: {error['error']}")
            
        else:
            # Use sequential downloader
            print(f"Downloading playlist: {playlist_info['title']} (sequential)")
            
            downloader = VideoDownloader(extractor)
            
            # Define progress callback for playlists
            def playlist_progress_callback(
                bytes_downloaded: int,
                total_bytes: int,
                elapsed: float,
                file_index: int = 1,
                total_files: int = 1,
                current_title: str = ""
            ) -> None:
                """Custom progress callback for playlists"""
                # Call the default progress callback
                default_progress_callback(
                    bytes_downloaded,
                    total_bytes,
                    elapsed,
                    file_index,
                    total_files,
                    current_title
                )
                
            output_files = downloader.download_playlist(
                args.url,
                output_path=args.output,
                quality=quality,
                progress_callback=playlist_progress_callback
            )
            
            print(f"\nPlaylist downloaded successfully")
            print(f"Downloaded {len(output_files)} videos to: {args.output}")
        
    except PlaylistUnavailableError as e:
        print(f"Error: Playlist unavailable - {str(e)}")
        sys.exit(1)
    except (ExtractionError, DownloadError) as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDownload canceled by user")
        sys.exit(1)

def search_youtube(args: argparse.Namespace) -> None:
    """
    Search YouTube for videos, channels, or playlists
    
    Args:
        args: Parsed command-line arguments
    """
    try:
        # Create search instance
        search = YouTubeSearch()
        
        # Perform search based on type
        print(f"Searching YouTube for: {args.query}")
        
        if args.type == 'video':
            results = search.search_videos(args.query, max_results=args.max_results, order=args.order)
        elif args.type == 'channel':
            results = search.search_channels(args.query, max_results=args.max_results, order=args.order)
        elif args.type == 'playlist':
            results = search.search_playlists(args.query, max_results=args.max_results, order=args.order)
        else:  # all
            results = search.search(args.query, max_results=args.max_results, order=args.order, type_filter='all')
            
        # Display results
        print(f"\nFound {len(results['items'])} results:")
        
        for i, item in enumerate(results['items']):
            print(f"{i+1}. {item['title']} ({item['type']})")
            if 'channel_title' in item:
                print(f"   Channel: {item['channel_title']}")
            print(f"   URL: {item['url']}")
            print()
            
        # Download the first video if requested
        if args.download and results['items'] and results['items'][0]['type'] == 'video':
            first_video = results['items'][0]
            print(f"Downloading first video: {first_video['title']}")
            
            # Create a new args namespace for the download
            download_args = argparse.Namespace(
                url=first_video['url'],
                output=args.output,
                quality=args.quality,
                filename=None,
                audio_only=False,
                video_only=False,
                format=None,
                list_formats=False
            )
            
            download_video(download_args)
            
    except ExtractionError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSearch canceled by user")
        sys.exit(1)

def get_video_info(args: argparse.Namespace) -> None:
    """
    Get and display information about a video or playlist
    
    Args:
        args: Parsed command-line arguments
    """
    try:
        # Create extractor
        extractor = YouTubeAPIExtractor()
        
        # Check if URL is a video or playlist
        if 'playlist' in args.url or 'list=' in args.url:
            # Get playlist info
            print(f"Fetching playlist info: {args.url}")
            playlist_info = extractor.extract_playlist_videos(args.url)
            
            print(f"\nPlaylist Information:")
            print(f"Title: {playlist_info['title']}")
            print(f"Video Count: {playlist_info['video_count']}")
            
            print("\nVideos in Playlist:")
            for i, video in enumerate(playlist_info['videos']):
                print(f"{i+1}. {video['title']}")
                if i >= 9:  # Show only the first 10 videos
                    print(f"... and {playlist_info['video_count'] - 10} more videos")
                    break
        else:
            # Get video info
            print(f"Fetching video info: {args.url}")
            video_info = extractor.extract_video_info(args.url)
            
            print(f"\nVideo Information:")
            print(f"Title: {video_info['title']}")
            print(f"Channel: {video_info['author']}")
            print(f"Duration: {video_info['length_seconds']} seconds ({format_duration(video_info['length_seconds'])})")
            print(f"Views: {video_info['views']:,}")
            print(f"URL: https://www.youtube.com/watch?v={video_info['id']}")
            
            # Show available formats summary
            print(f"\nAvailable Formats Summary:")
            
            # Group formats by type
            video_formats = [f for f in video_info['formats'] if f['is_video']]
            audio_formats = [f for f in video_info['formats'] if f['is_audio'] and not f['is_video']]
            combined_formats = [f for f in video_info['formats'] if f['is_audio'] and f['is_video']]
            
            # Show video formats
            if video_formats:
                print("\nVideo-only formats:")
                resolutions = set(f.get('height', 0) for f in video_formats)
                containers = set(f.get('container', '') for f in video_formats)
                codecs = set(f.get('codecs', '').split(',')[0].strip() for f in video_formats)
                
                print(f"  Resolutions: {', '.join(sorted(str(r) + 'p' for r in resolutions if r > 0))}")
                print(f"  Containers: {', '.join(sorted(containers))}")
                print(f"  Codecs: {', '.join(sorted(codecs))}")
                
            # Show audio formats
            if audio_formats:
                print("\nAudio-only formats:")
                bitrates = set(int(f.get('audio_bitrate', 0) / 1000) for f in audio_formats)
                containers = set(f.get('container', '') for f in audio_formats)
                codecs = set(f.get('codecs', '') for f in audio_formats)
                
                print(f"  Bitrates: {', '.join(sorted(str(r) + ' kbps' for r in bitrates if r > 0))}")
                print(f"  Containers: {', '.join(sorted(containers))}")
                print(f"  Codecs: {', '.join(sorted(codecs))}")
                
            # Show combined formats
            if combined_formats:
                print("\nCombined audio+video formats:")
                resolutions = set(f.get('height', 0) for f in combined_formats)
                containers = set(f.get('container', '') for f in combined_formats)
                
                print(f"  Resolutions: {', '.join(sorted(str(r) + 'p' for r in resolutions if r > 0))}")
                print(f"  Containers: {', '.join(sorted(containers))}")
            
            print("\nTo see all formats in detail, use: skt-dl download {args.url} --list-formats")
            
    except (VideoUnavailableError, PlaylistUnavailableError) as e:
        print(f"Error: Content unavailable - {str(e)}")
        sys.exit(1)
    except ExtractionError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation canceled by user")
        sys.exit(1)

def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:d}:{seconds:02d}"

def guess_command_type(url: str) -> str:
    """
    Guess if the URL is a video, playlist, or channel
    
    Args:
        url: YouTube URL
        
    Returns:
        Type of URL ("video", "playlist", or "channel")
    """
    if 'playlist' in url or 'list=' in url:
        return 'playlist'
    elif 'channel' in url or 'user' in url or 'c/' in url:
        return 'channel'
    else:
        return 'video'

def download_subtitles(args: argparse.Namespace) -> None:
    """
    Download subtitles for a video
    
    Args:
        args: Parsed command-line arguments
    """
    try:
        # Create API extractor and subtitle downloader
        api_extractor = YouTubeAPIExtractor()
        subtitle_downloader = SubtitleDownloader(api_extractor)
        
        # List available subtitles if requested
        if args.list:
            print(f"Listing available subtitles for: {args.url}")
            available_captions = subtitle_downloader.list_available_captions(args.url)
            
            if not available_captions:
                print("No subtitles available for this video.")
                return
                
            print(f"\nFound {len(available_captions)} subtitle tracks:")
            for i, caption in enumerate(available_captions):
                auto_gen = " (auto-generated)" if caption.get("is_auto_generated") else ""
                translatable = " (translatable)" if caption.get("is_translatable") else ""
                print(f"{i+1}. {caption.get('name')} ({caption.get('language_code')}){auto_gen}{translatable}")
                
            return
        
        # Download the subtitles
        print(f"Downloading {args.language} subtitles for: {args.url}")
        
        output_file = subtitle_downloader.download_subtitle(
            video_url=args.url,
            language_code=args.language,
            output_path=args.output,
            filename=args.filename,
            format=args.format
        )
        
        if output_file:
            print(f"\nSubtitles downloaded successfully to: {output_file}")
        else:
            print(f"\nNo {args.language} subtitles available for this video.")
            print("Use '--list' to see available subtitle languages.")
            
    except ExtractionError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDownload canceled by user")
        sys.exit(1)

def download_thumbnails(args: argparse.Namespace) -> None:
    """
    Download thumbnails for a video
    
    Args:
        args: Parsed command-line arguments
    """
    try:
        # Create API extractor and thumbnail downloader
        api_extractor = YouTubeAPIExtractor()
        thumbnail_downloader = ThumbnailDownloader(api_extractor)
        
        if args.all:
            # Download all thumbnail qualities
            print(f"Downloading all thumbnail qualities for: {args.url}")
            
            output_files = thumbnail_downloader.download_all_thumbnails(
                video_url=args.url,
                output_path=args.output,
                filename=args.filename
            )
            
            print(f"\nDownloaded {len(output_files)} thumbnails:")
            for quality, path in output_files.items():
                print(f"  {quality}: {path}")
                
        else:
            # Download specific quality
            print(f"Downloading {args.quality} thumbnail for: {args.url}")
            
            output_file = thumbnail_downloader.download_thumbnail(
                video_url=args.url,
                output_path=args.output,
                quality=args.quality,
                filename=args.filename
            )
            
            print(f"\nThumbnail downloaded successfully to: {output_file}")
            
    except (ExtractionError, DownloadError) as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDownload canceled by user")
        sys.exit(1)

def main() -> None:
    """
    Main CLI entry point
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Configure logging
    configure_logging(args.verbose if hasattr(args, 'verbose') else False)
    
    # Show version information if requested
    if hasattr(args, 'version') and args.version:
        show_version()
        return
        
    # Execute the appropriate command
    if hasattr(args, 'command') and args.command:
        if args.command == 'download':
            # Check for subtitle-only or thumbnail-only flags
            if args.subtitles_only:
                # Create temporary args for subtitle command
                subtitle_args = argparse.Namespace(
                    url=args.url,
                    output=args.output,
                    filename=args.filename,
                    language=args.subtitle_lang,
                    format=args.subtitle_format,
                    list=False
                )
                download_subtitles(subtitle_args)
                return
                
            elif args.thumbnail_only:
                # Create temporary args for thumbnail command
                thumbnail_args = argparse.Namespace(
                    url=args.url,
                    output=args.output,
                    filename=args.filename,
                    quality=args.thumbnail_quality,
                    all=args.all_thumbnails
                )
                download_thumbnails(thumbnail_args)
                return
                
            # Normal video download with potential extras
            download_video(args)
            
            # Download subtitles if requested
            if args.with_subtitles:
                subtitle_args = argparse.Namespace(
                    url=args.url,
                    output=args.output,
                    filename=args.filename,
                    language=args.subtitle_lang,
                    format=args.subtitle_format,
                    list=False
                )
                download_subtitles(subtitle_args)
                
            # Download thumbnail if requested
            if args.with_thumbnail:
                thumbnail_args = argparse.Namespace(
                    url=args.url,
                    output=args.output,
                    filename=args.filename,
                    quality=args.thumbnail_quality,
                    all=args.all_thumbnails
                )
                download_thumbnails(thumbnail_args)
                
        elif args.command == 'search':
            search_youtube(args)
        elif args.command == 'info':
            get_video_info(args)
        elif args.command == 'subtitle':
            download_subtitles(args)
        elif args.command == 'thumbnail':
            download_thumbnails(args)
    else:
        # No command specified
        if len(sys.argv) <= 1 or (hasattr(args, 'version') and args.version):
            # Show help if no arguments provided
            print("skt-dl: A custom YouTube video and playlist downloader")
            print(f"Version: {__version__}")
            print("\nFor usage help, run: skt-dl --help")
        else:
            print("No valid command specified.")
            print("Use 'skt-dl --help' for usage information.")
            sys.exit(1)

if __name__ == "__main__":
    main()