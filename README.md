# skt-dl - YouTube Downloader

A lightweight, pure Python library and command-line tool for downloading YouTube videos.

## Features

- Download YouTube videos in various qualities (144p to 4K)
- Download audio-only streams (MP3, AAC, Opus)
- Download playlists
- Search YouTube videos, channels, and playlists
- Extract video information
- Support for multiple format types (MP4, WebM)
- Support for multiple codecs (H.264, VP9, AV1)

## Installation

```bash
# Install from source
git clone https://github.com/username/skt-dl.git
cd skt-dl
pip install -e .
```

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

# Get video information
skt-dl info https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Search YouTube
skt-dl search "python tutorial"

# Search and download the first result
skt-dl search "python tutorial" --download
```

### Python Module Usage

```python
# Import the package
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
```

## API Key (Optional)

For improved reliability, skt-dl can use the YouTube Data API v3:

1. Get an API key from the [Google Cloud Console](https://console.cloud.google.com/)
2. Set it as an environment variable:

```bash
export YOUTUBE_API_KEY="your-api-key"
```

## Requirements

- Python 3.8 or higher
- requests

## License

MIT