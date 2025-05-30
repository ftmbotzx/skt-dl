# skt-dl - YouTube Downloader

A lightweight, pure Python library and command-line tool for downloading YouTube videos.

## Features

- Download YouTube videos in various qualities (144p to 4K)
- Download audio-only streams (MP3, AAC, Opus)
- Download playlists with sequential or concurrent processing
- Search YouTube videos, channels, and playlists
- Extract video information with advanced metadata
- Download video subtitles/captions in various formats (SRT, VTT, JSON, XML)
- Download video thumbnails in various qualities
- Support for multiple format types (MP4, WebM)
- Support for multiple codecs (H.264, VP9, AV1)
- Enhanced progress tracking with terminal-aware display
- Compatibility layer with youtube-dl/yt-dlp via `YoutubeDL` class

## Installation

You can install skt-dl directly from GitHub:

```bash
pip install git+https://github.com/example/skt-dl.git
```

Or install from the source code:

```bash
git clone https://github.com/example/skt-dl.git
cd skt-dl
pip install -e .
```

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

For instructions on building and deploying the package, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Usage

### Command-line Usage

```bash
# Show help
skt-dl --help

# Download a video (default: best quality)
skt-dl download https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Specify output directory and quality
skt-dl download https://www.youtube.com/watch?v=dQw4w9WgXcQ -o ~/Downloads -q 720p

# Download audio only
skt-dl download https://www.youtube.com/watch?v=dQw4w9WgXcQ --audio-only

# List available formats
skt-dl download https://www.youtube.com/watch?v=dQw4w9WgXcQ --list-formats

# Download specific format using itag
skt-dl download https://www.youtube.com/watch?v=dQw4w9WgXcQ -q itag:251

# Download a playlist
skt-dl download https://www.youtube.com/playlist?list=PLexamplelist

# Download a playlist with concurrent processing
skt-dl download https://www.youtube.com/playlist?list=PLexamplelist --concurrent --max-workers 4

# Download video with subtitles
skt-dl download https://www.youtube.com/watch?v=dQw4w9WgXcQ --with-subtitles

# Download only subtitles
skt-dl subtitle https://www.youtube.com/watch?v=dQw4w9WgXcQ -l en --format srt

# List available subtitle languages
skt-dl subtitle https://www.youtube.com/watch?v=dQw4w9WgXcQ --list

# Download video thumbnail
skt-dl thumbnail https://www.youtube.com/watch?v=dQw4w9WgXcQ -q high

# Download all thumbnail qualities
skt-dl thumbnail https://www.youtube.com/watch?v=dQw4w9WgXcQ --all

# Get video information
skt-dl info https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Search YouTube
skt-dl search "python tutorial"

# Search and download the first result
skt-dl search "python tutorial" --download
```

### Python Module Usage

```python
# Basic video download
from skt_dl import YouTubeAPIExtractor, VideoDownloader

# Create extractor and downloader
extractor = YouTubeAPIExtractor()
downloader = VideoDownloader(extractor)

# Download a video
video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
output_file = downloader.download_video(
    url=video_url,
    output_path="downloads",
    quality="720p"
)
print(f"Downloaded to: {output_file}")

# Search for videos
from skt_dl import YouTubeSearch

search = YouTubeSearch()
results = search.search_videos("python tutorial", max_results=5)
for video in results['items']:
    print(f"{video['title']} - {video['url']}")

# Download subtitles
from skt_dl import SubtitleDownloader

subtitle_downloader = SubtitleDownloader(extractor)
subtitle_file = subtitle_downloader.download_subtitle(
    video_url=video_url,
    language_code="en",
    output_path="downloads",
    format="srt"
)
print(f"Subtitles downloaded to: {subtitle_file}")

# Download thumbnails
from skt_dl import ThumbnailDownloader

thumbnail_downloader = ThumbnailDownloader(extractor)
thumbnail_file = thumbnail_downloader.download_thumbnail(
    video_url=video_url,
    output_path="downloads",
    quality="high"
)
print(f"Thumbnail downloaded to: {thumbnail_file}")

# Concurrent playlist download
from skt_dl import ConcurrentDownloader

concurrent_downloader = ConcurrentDownloader(max_workers=4)
downloaded_files, errors = concurrent_downloader.download_playlist(
    playlist_url="https://www.youtube.com/playlist?list=PLexamplelist",
    output_path="downloads",
    quality="720p"
)
print(f"Downloaded {len(downloaded_files)} videos")
```

## API Key (Optional)

For improved reliability, skt-dl can use the YouTube Data API v3:

1. Get an API key from the [Google Cloud Console](https://console.cloud.google.com/)
2. Set it as an environment variable:

```bash
export YOUTUBE_API_KEY="your-api-key"
```

## Web Interface

skt-dl also comes with a web interface for those who prefer a graphical interface over command-line tools.

To start the web interface:

```bash
skt-dl-web
```

This will launch a local web server on http://localhost:5000 where you can:

- Download videos and playlists
- Search YouTube
- Extract video information
- Download subtitles and thumbnails
- Use concurrent processing for playlists

### Web Interface Configuration

You can configure the web interface using environment variables:

- `SKT_DL_DOWNLOAD_DIR`: Directory where downloads are saved (default: ~/skt-dl-downloads)
- `PORT`: Port to run the web server on (default: 5000)
- `SKT_DL_PRODUCTION`: Set to "true" to run in production mode
- `SESSION_SECRET`: Secret key for Flask sessions

## Requirements

- Python 3.8 or higher
- requests
- flask (for web interface)
- gunicorn (for web interface in production)

## License

MIT