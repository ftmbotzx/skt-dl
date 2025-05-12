# skt-dl

A custom-built Python command-line tool and library for downloading YouTube videos and playlists without relying on external downloading libraries.

## Features

- Custom-built YouTube video extraction engine
- Command line interface for downloading YouTube videos
- Support for downloading individual videos
- Support for downloading playlists
- Video quality selection options
- Progress tracking for downloads
- Error handling for rate limits and unavailable videos
- Exportable as a Python package

## Installation

You can install skt-dl with pip:

```bash
pip install skt-dl
```

Or install directly from the repository:

```bash
pip install git+https://github.com/your-username/skt-dl.git
```

## Command Line Usage

### Basic Usage

Download a YouTube video with the highest quality:

```bash
skt-dl "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Specify Quality

```bash
skt-dl "https://www.youtube.com/watch?v=VIDEO_ID" -q 720p
```

Available quality options: `best`, `worst`, or specific resolutions like `720p`, `1080p`

### Download to Specific Directory

```bash
skt-dl "https://www.youtube.com/watch?v=VIDEO_ID" -o /path/to/directory
```

### Download Playlist

```bash
skt-dl "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

### Custom Filename

```bash
skt-dl "https://www.youtube.com/watch?v=VIDEO_ID" -f "my-custom-filename"
```

### Show Help

```bash
skt-dl --help
```

## Library Usage

You can also use skt-dl as a Python library in your own projects:

```python
from skt_dl import VideoDownloader

# Create a downloader instance
downloader = VideoDownloader()

# Download a video
output_file = downloader.download_video(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    output_path=".",
    quality="best"
)

print(f"Video downloaded to: {output_file}")

# Extract video info without downloading
video_info = downloader.extractor.extract_video_info("https://www.youtube.com/watch?v=VIDEO_ID")
print(f"Title: {video_info['title']}")
print(f"Author: {video_info['author']}")
print(f"Duration: {video_info['length_seconds']} seconds")
```

See the `example_usage.py` file for more detailed examples.

## Requirements

- Python 3.8 or newer
- `requests` library

## License

MIT

## Disclaimer

This tool is for educational and personal use only. Please respect YouTube's Terms of Service and copyright laws when using this tool.