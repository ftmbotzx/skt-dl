#!/usr/bin/env python3
"""
Example usage of the skt-dl library
"""

from skt_dl import VideoDownloader
from skt_dl.downloader import default_progress_callback

def main():
    """
    Demonstrate the basic usage of skt-dl library
    """
    print("skt-dl Library Example Usage")
    print("----------------------------")
    
    # Create a downloader instance
    downloader = VideoDownloader()
    
    # Example URL (replace with a valid YouTube URL)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley
    
    print(f"Downloading video: {video_url}")
    
    try:
        # Download the video with the default progress callback
        output_file = downloader.download_video(
            video_url,
            output_path=".",
            quality="best",
            progress_callback=default_progress_callback
        )
        
        print(f"\nVideo downloaded successfully to: {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    # Example of extracting video info without downloading
    print("\nExtracting video info...")
    try:
        video_info = downloader.extractor.extract_video_info(video_url)
        
        print(f"Title: {video_info['title']}")
        print(f"Author: {video_info['author']}")
        print(f"Duration: {video_info['length_seconds']} seconds")
        print(f"Thumbnail URL: {video_info['thumbnail']}")
        print(f"Available formats: {len(video_info['formats'])}")
        
        # Print details of the top 3 formats
        print("\nTop 3 formats:")
        for fmt in video_info['formats'][:3]:
            print(f"  - {fmt['quality']} ({fmt['container']}): {fmt['mime_type']}")
        
    except Exception as e:
        print(f"Error extracting video info: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())