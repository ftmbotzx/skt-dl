"""
Module for concurrent download operations
"""

import os
import logging
import threading
import queue
from typing import List, Dict, Callable, Optional, Tuple, Any

from .downloader import VideoDownloader
from .exceptions import DownloadError, PlaylistUnavailableError
from .api_extractor import YouTubeAPIExtractor

logger = logging.getLogger('skt-dl.concurrent')

class ConcurrentDownloader:
    """
    Class for concurrent downloads of multiple videos or playlists
    """
    
    def __init__(self, max_workers: int = 4, extractor: Optional[YouTubeAPIExtractor] = None):
        """
        Initialize the concurrent downloader
        
        Args:
            max_workers: Maximum number of concurrent download workers
            extractor: Optional extractor instance to use
        """
        self.max_workers = max_workers
        self.extractor = extractor or YouTubeAPIExtractor()
        self.downloader = VideoDownloader(self.extractor)
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.running = False
        self.errors = []
        self.completed = []
        
    def download_playlist(
        self,
        playlist_url: str,
        output_path: str = ".",
        quality: str = "best",
        progress_callback: Optional[Callable] = None
    ) -> Tuple[List[str], List[Dict]]:
        """
        Download a playlist concurrently
        
        Args:
            playlist_url: YouTube playlist URL
            output_path: Directory to save the downloaded files
            quality: Quality to download
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (list of downloaded files, list of errors)
        """
        logger.info(f"Starting concurrent download for playlist: {playlist_url}")
        
        # Extract playlist information
        try:
            playlist_info = self.extractor.extract_playlist_videos(playlist_url)
            videos = playlist_info.get('videos', [])
            total_videos = len(videos)
            
            if not videos:
                raise PlaylistUnavailableError("No videos found in playlist")
                
            logger.info(f"Found {total_videos} videos in playlist")
            
            # Create the output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Start worker threads
            self._start_workers()
            
            # Add download tasks to the queue
            for i, video in enumerate(videos):
                video_url = video.get('url', '')
                video_title = video.get('title', f'video_{i+1}')
                
                # Create a task
                task = {
                    'type': 'video',
                    'url': video_url,
                    'output_path': output_path,
                    'quality': quality,
                    'index': i + 1,
                    'total': total_videos,
                    'title': video_title,
                    'progress_callback': progress_callback
                }
                
                # Add task to the queue
                self.task_queue.put(task)
            
            # Wait for all tasks to complete
            self.task_queue.join()
            
            # Stop workers
            self._stop_workers()
            
            # Process results
            downloaded_files = []
            errors = []
            
            while not self.result_queue.empty():
                result = self.result_queue.get()
                if result.get('success', False):
                    downloaded_files.append(result.get('output_file', ''))
                else:
                    errors.append({
                        'url': result.get('url', ''),
                        'error': result.get('error', 'Unknown error'),
                        'index': result.get('index', 0),
                        'title': result.get('title', '')
                    })
                    
            logger.info(f"Playlist download completed: {len(downloaded_files)} success, {len(errors)} failures")
            
            return (downloaded_files, errors)
            
        except Exception as e:
            logger.error(f"Error in concurrent playlist download: {str(e)}")
            self._stop_workers()
            raise
    
    def _worker(self):
        """
        Worker thread function to process download tasks
        """
        while self.running:
            try:
                # Get a task from the queue with a timeout
                # This allows the thread to check the running flag periodically
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the task
                try:
                    if task['type'] == 'video':
                        # Extract task parameters
                        url = task['url']
                        output_path = task['output_path']
                        quality = task['quality']
                        index = task.get('index', 0)
                        total = task.get('total', 0)
                        title = task.get('title', '')
                        progress_callback = task.get('progress_callback')
                        
                        # Create a wrapper progress callback if needed
                        wrapped_callback = None
                        if progress_callback:
                            # Define a function that adapts the parameters
                            def wrapped_cb(bytes_downloaded, total_bytes, elapsed):
                                progress_callback(
                                    bytes_downloaded,
                                    total_bytes,
                                    elapsed,
                                    index,
                                    total,
                                    title
                                )
                            wrapped_callback = wrapped_cb
                                
                        # Download the video
                        logger.info(f"Worker downloading video {index}/{total}: {title}")
                        output_file = self.downloader.download_video(
                            url=url,
                            output_path=output_path,
                            quality=quality,
                            progress_callback=wrapped_callback
                        )
                        
                        # Add successful result to results queue
                        self.result_queue.put({
                            'success': True,
                            'url': url,
                            'output_file': output_file,
                            'index': index,
                            'title': title
                        })
                        
                        logger.info(f"Worker completed video {index}/{total}: {title}")
                        
                except Exception as e:
                    # Add error result to results queue
                    logger.error(f"Worker error: {str(e)}")
                    self.result_queue.put({
                        'success': False,
                        'url': task.get('url', ''),
                        'error': str(e),
                        'index': task.get('index', 0),
                        'title': task.get('title', '')
                    })
                
                # Mark the task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Unhandled worker error: {str(e)}")
                
    def _start_workers(self):
        """
        Start worker threads
        """
        logger.info(f"Starting {self.max_workers} worker threads")
        self.running = True
        self.workers = []
        
        for i in range(self.max_workers):
            thread = threading.Thread(target=self._worker, daemon=True)
            thread.start()
            self.workers.append(thread)
            
    def _stop_workers(self):
        """
        Stop worker threads
        """
        logger.info("Stopping worker threads")
        self.running = False
        
        # Wait for all worker threads to complete
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=2.0)
                
        self.workers = []