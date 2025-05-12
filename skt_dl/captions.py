"""
Module for downloading and processing YouTube subtitles/captions
"""

import os
import re
import json
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union, Tuple
from urllib.parse import unquote

import requests

from .utils import safe_filename, retry_on_rate_limit
from .exceptions import ExtractionError
from .api_extractor import YouTubeAPIExtractor

logger = logging.getLogger('skt-dl.captions')

class SubtitleDownloader:
    """
    Class for downloading and converting YouTube subtitles
    """
    
    def __init__(self, api_extractor: Optional[YouTubeAPIExtractor] = None):
        """
        Initialize the subtitle downloader
        
        Args:
            api_extractor: Optional YouTubeAPIExtractor instance to use
        """
        self.api_extractor = api_extractor
        self.session = requests.Session()
        
    def list_available_captions(self, video_url: str) -> List[Dict]:
        """
        List available subtitles for a video
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            List of available subtitle tracks with language info
        """
        try:
            # Get the video page to extract captions info
            response = self.session.get(video_url, timeout=30)
            html = response.text
            
            # Try to extract the captions info from the player response
            captions_regex = r'captionTracks":\s*(\[.*?\])'
            captions_match = re.search(captions_regex, html)
            
            if not captions_match:
                logger.warning("Could not find captions data in video page")
                return []
                
            # Parse the JSON captions data
            try:
                captions_json = json.loads(captions_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Could not parse captions JSON data")
                return []
                
            # Format the captions info
            captions_list = []
            for caption in captions_json:
                caption_info = {
                    "name": caption.get("name", {}).get("simpleText", ""),
                    "language_code": caption.get("languageCode", ""),
                    "base_url": caption.get("baseUrl", ""),
                    "is_translatable": caption.get("isTranslatable", False),
                    "is_auto_generated": "auto-generated" in caption.get("name", {}).get("simpleText", "").lower()
                }
                captions_list.append(caption_info)
                
            return captions_list
                
        except Exception as e:
            logger.error(f"Error getting captions list: {str(e)}")
            return []
            
    def download_subtitle(
        self, 
        video_url: str, 
        language_code: str = "en", 
        output_path: str = ".", 
        filename: Optional[str] = None,
        format: str = "srt"
    ) -> str:
        """
        Download subtitles for a video
        
        Args:
            video_url: YouTube video URL
            language_code: Language code to download (e.g., "en", "es", "fr")
            output_path: Directory to save the subtitle file
            filename: Optional custom filename (without extension)
            format: Output format ("srt", "vtt", "json", "xml")
            
        Returns:
            Path to the downloaded subtitle file or empty string if failed
            
        Raises:
            ExtractionError: If subtitles cannot be extracted
        """
        logger.info(f"Downloading {language_code} subtitles for {video_url}")
        
        # Get available captions
        captions = self.list_available_captions(video_url)
        if not captions:
            logger.warning(f"No captions found for video: {video_url}")
            return ""
            
        # Find the requested language
        caption_info = None
        for cap in captions:
            if cap["language_code"] == language_code:
                caption_info = cap
                break
                
        if not caption_info:
            # Try to find a close match
            for cap in captions:
                if cap["language_code"].startswith(language_code) or language_code.startswith(cap["language_code"]):
                    caption_info = cap
                    logger.info(f"Using similar language: {cap['language_code']} instead of {language_code}")
                    break
                    
        if not caption_info:
            logger.warning(f"No captions found for language: {language_code}")
            return ""
            
        # Get video title if needed for filename
        if not filename and self.api_extractor:
            try:
                video_info = self.api_extractor.extract_video_info(video_url)
                video_title = video_info.get("title", "subtitle")
            except Exception:
                video_title = "subtitle"
        else:
            video_title = "subtitle"
            
        # Create filename
        if not filename:
            filename = safe_filename(f"{video_title}.{language_code}")
            
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Download the subtitle file in XML format
        base_url = caption_info["base_url"]
        
        # Add format parameter if needed
        if format == "xml":
            subtitle_url = base_url
        elif format == "vtt":
            subtitle_url = f"{base_url}&fmt=vtt"
        else:  # Default to XML for conversion
            subtitle_url = base_url
            
        try:
            response = self.session.get(subtitle_url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to download subtitles: HTTP {response.status_code}")
                return ""
                
            # Process the subtitle content based on requested format
            if format == "xml":
                subtitle_content = response.text
                output_file = os.path.join(output_path, f"{filename}.xml")
            elif format == "vtt":
                subtitle_content = response.text
                output_file = os.path.join(output_path, f"{filename}.vtt")
            elif format == "json":
                xml_content = response.text
                json_content = self._convert_xml_to_json(xml_content)
                subtitle_content = json.dumps(json_content, indent=2)
                output_file = os.path.join(output_path, f"{filename}.json")
            else:  # SRT format
                xml_content = response.text
                srt_content = self._convert_xml_to_srt(xml_content)
                subtitle_content = srt_content
                output_file = os.path.join(output_path, f"{filename}.srt")
                
            # Write to file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(subtitle_content)
                
            logger.info(f"Subtitles downloaded to: {output_file}")
            return output_file
                
        except Exception as e:
            logger.error(f"Error downloading subtitles: {str(e)}")
            return ""
            
    def _convert_xml_to_srt(self, xml_content: str) -> str:
        """
        Convert YouTube XML subtitle format to SRT
        
        Args:
            xml_content: YouTube XML subtitle content
            
        Returns:
            SRT formatted subtitle content
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            srt_lines = []
            
            for i, element in enumerate(root.findall(".//text")):
                # Get start time and duration in seconds
                start = float(element.get("start", "0"))
                duration = float(element.get("dur", "0")) if element.get("dur") else 0
                end = start + duration
                
                # Convert to SRT time format (HH:MM:SS,mmm)
                start_time = self._format_srt_time(start)
                end_time = self._format_srt_time(end)
                
                # Get the subtitle text and decode HTML entities
                text = element.text if element.text else ""
                text = self._decode_html_entities(text)
                
                # Add subtitle entry
                srt_lines.append(str(i + 1))
                srt_lines.append(f"{start_time} --> {end_time}")
                srt_lines.append(text)
                srt_lines.append("")  # Empty line between entries
                
            return "\n".join(srt_lines)
            
        except Exception as e:
            logger.error(f"Error converting XML to SRT: {str(e)}")
            return ""
            
    def _convert_xml_to_json(self, xml_content: str) -> List[Dict]:
        """
        Convert YouTube XML subtitle format to JSON
        
        Args:
            xml_content: YouTube XML subtitle content
            
        Returns:
            JSON-serializable list of subtitle entries
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            json_subtitles = []
            
            for element in root.findall(".//text"):
                # Get start time and duration in seconds
                start = float(element.get("start", "0"))
                duration = float(element.get("dur", "0")) if element.get("dur") else 0
                end = start + duration
                
                # Get the subtitle text and decode HTML entities
                text = element.text if element.text else ""
                text = self._decode_html_entities(text)
                
                # Add subtitle entry
                json_subtitles.append({
                    "start": start,
                    "end": end,
                    "duration": duration,
                    "text": text
                })
                
            return json_subtitles
            
        except Exception as e:
            logger.error(f"Error converting XML to JSON: {str(e)}")
            return []
            
    def _format_srt_time(self, seconds: float) -> str:
        """
        Format time in seconds to SRT time format (HH:MM:SS,mmm)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
        
    def _decode_html_entities(self, text: str) -> str:
        """
        Decode HTML entities in subtitle text
        
        Args:
            text: Text with HTML entities
            
        Returns:
            Decoded text
        """
        # Basic HTML entity decoding
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", "\"")
        text = text.replace("&#39;", "'")
        
        # URL decoding
        return unquote(text)