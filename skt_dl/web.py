"""
Flask web interface for skt-dl YouTube downloader
"""

import os
import json
import logging
from urllib.parse import urlparse, parse_qs

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, Response, send_file
from werkzeug.utils import secure_filename

from .api_extractor import YouTubeAPIExtractor
from .downloader import VideoDownloader
from .captions import SubtitleDownloader
from .thumbnail import ThumbnailDownloader
from .concurrent import ConcurrentDownloader
from .search import YouTubeSearch

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('skt-dl-web')

# Import constants
from .constants import DEFAULT_DOWNLOAD_DIR, TEMPLATES_DIR, STATIC_DIR

# Initialize Flask app
app = Flask(__name__, 
           template_folder=TEMPLATES_DIR,
           static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SESSION_SECRET", "skt-dl-secret-key")

def get_download_dir():
    """Get the download directory, creating it if it doesn't exist"""
    download_dir = os.environ.get("SKT_DL_DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR)
    os.makedirs(download_dir, exist_ok=True)
    return download_dir

# Initialize the YouTube API extractor
extractor = YouTubeAPIExtractor()
downloader = VideoDownloader(extractor)
subtitle_downloader = SubtitleDownloader(extractor)
thumbnail_downloader = ThumbnailDownloader(extractor)
search = YouTubeSearch()

@app.route('/')
def index():
    """
    Render the main page
    """
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_info():
    """
    Extract information about a YouTube video or playlist
    """
    url = request.form.get('url', '')
    
    if not url:
        flash('Please enter a YouTube URL', 'error')
        return redirect(url_for('index'))
    
    try:
        # Determine if URL is a video or playlist
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'list' in query_params:
            # This is a playlist
            playlist_info = extractor.extract_playlist_videos(url)
            session['info_type'] = 'playlist'
            session['info'] = json.dumps(playlist_info)
            return redirect(url_for('show_playlist_info'))
        else:
            # This is a video
            video_info = extractor.extract_video_info(url)
            session['info_type'] = 'video'
            session['info'] = json.dumps(video_info)
            return redirect(url_for('show_video_info'))
            
    except Exception as e:
        logger.error(f"Error extracting info: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/video-info')
def show_video_info():
    """
    Show information about a video
    """
    if 'info' not in session or 'info_type' not in session or session['info_type'] != 'video':
        flash('No video information available', 'error')
        return redirect(url_for('index'))
    
    try:
        video_info = json.loads(session['info'])
        return render_template('video_info.html', video=video_info)
    except Exception as e:
        logger.error(f"Error displaying video info: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/playlist-info')
def show_playlist_info():
    """
    Show information about a playlist
    """
    if 'info' not in session or 'info_type' not in session or session['info_type'] != 'playlist':
        flash('No playlist information available', 'error')
        return redirect(url_for('index'))
    
    try:
        playlist_info = json.loads(session['info'])
        return render_template('playlist_info.html', playlist=playlist_info)
    except Exception as e:
        logger.error(f"Error displaying playlist info: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/download-video', methods=['POST'])
def download_video():
    """
    Download a video with specified options
    """
    if 'info' not in session or 'info_type' not in session or session['info_type'] != 'video':
        flash('No video information available', 'error')
        return redirect(url_for('index'))
    
    try:
        video_info = json.loads(session['info'])
        video_url = video_info.get('url', '')
        
        quality = request.form.get('quality', 'best')
        audio_only = request.form.get('audio_only') == 'on'
        video_only = request.form.get('video_only') == 'on'
        with_subtitles = request.form.get('with_subtitles') == 'on'
        with_thumbnail = request.form.get('with_thumbnail') == 'on'
        
        if audio_only:
            quality = 'audio'
        elif video_only:
            quality = 'video'
        
        download_dir = get_download_dir()
        
        # Download the video
        output_file = downloader.download_video(
            url=video_url,
            output_path=download_dir,
            quality=quality
        )
        
        # Download subtitles if requested
        subtitle_file = None
        if with_subtitles:
            subtitle_file = subtitle_downloader.download_subtitle(
                video_url=video_url,
                language_code='en',
                output_path=download_dir
            )
        
        # Download thumbnail if requested
        thumbnail_file = None
        if with_thumbnail:
            thumbnail_file = thumbnail_downloader.download_thumbnail(
                video_url=video_url,
                output_path=download_dir
            )
        
        # Store download results in session
        session['download_result'] = {
            'video_file': output_file,
            'subtitle_file': subtitle_file,
            'thumbnail_file': thumbnail_file
        }
        
        flash('Download completed successfully!', 'success')
        return redirect(url_for('download_result'))
        
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('show_video_info'))

@app.route('/download-playlist', methods=['POST'])
def download_playlist():
    """
    Download a playlist with specified options
    """
    if 'info' not in session or 'info_type' not in session or session['info_type'] != 'playlist':
        flash('No playlist information available', 'error')
        return redirect(url_for('index'))
    
    try:
        playlist_info = json.loads(session['info'])
        playlist_url = playlist_info.get('url', '')
        
        quality = request.form.get('quality', 'best')
        audio_only = request.form.get('audio_only') == 'on'
        video_only = request.form.get('video_only') == 'on'
        use_concurrent = request.form.get('use_concurrent') == 'on'
        max_workers = int(request.form.get('max_workers', '4'))
        
        if audio_only:
            quality = 'audio'
        elif video_only:
            quality = 'video'
        
        download_dir = get_download_dir()
        
        # Download the playlist
        if use_concurrent:
            concurrent_downloader = ConcurrentDownloader(max_workers=max_workers, extractor=extractor)
            downloaded_files, errors = concurrent_downloader.download_playlist(
                playlist_url=playlist_url,
                output_path=download_dir,
                quality=quality
            )
            
            # Store download results in session
            session['download_result'] = {
                'playlist': True,
                'files': downloaded_files,
                'errors': len(errors),
                'total': len(downloaded_files) + len(errors)
            }
        else:
            output_files = downloader.download_playlist(
                playlist_url,
                output_path=download_dir,
                quality=quality
            )
            
            # Store download results in session
            session['download_result'] = {
                'playlist': True,
                'files': output_files,
                'errors': 0,
                'total': len(output_files)
            }
        
        flash('Playlist download completed successfully!', 'success')
        return redirect(url_for('download_result'))
        
    except Exception as e:
        logger.error(f"Error downloading playlist: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('show_playlist_info'))

@app.route('/download-result')
def download_result():
    """
    Show download results
    """
    if 'download_result' not in session:
        flash('No download results available', 'error')
        return redirect(url_for('index'))
    
    try:
        result = session['download_result']
        return render_template('download_result.html', result=result)
    except Exception as e:
        logger.error(f"Error displaying download result: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])
def search_videos():
    """
    Search for YouTube videos
    """
    if request.method == 'POST':
        query = request.form.get('query', '')
        
        if not query:
            flash('Please enter a search query', 'error')
            return redirect(url_for('search_videos'))
        
        try:
            # Search for videos
            results = search.search_videos(query, max_results=10)
            return render_template('search_results.html', results=results, query=query)
        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            flash(f"Error: {str(e)}", 'error')
            return redirect(url_for('search_videos'))
    else:
        return render_template('search.html')

@app.route('/download-file/<path:filename>')
def download_file(filename):
    """
    Download a file from the downloads directory
    """
    try:
        download_dir = get_download_dir()
        filepath = os.path.join(download_dir, secure_filename(os.path.basename(filename)))
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

def run_app():
    """
    Run the Flask application
    """
    # Create the download directory
    get_download_dir()
    
    # Check if running in a production environment
    if os.environ.get('SKT_DL_PRODUCTION', '').lower() == 'true':
        # Production setup
        print("Running in production mode")
        print(f"Download directory: {get_download_dir()}")
        return app
    else:
        # Development setup
        print("Running in development mode")
        print(f"Download directory: {get_download_dir()}")
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=True, host='0.0.0.0', port=port)

if __name__ == '__main__':
    run_app()