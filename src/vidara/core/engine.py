"""
Handles the orchestration of the application workflow.

This module unifies the network client and download tool interactions
into a single harmonious process.
"""

from .client import VidaraClient
from .downloader import FFmpegDownloader
from ..models import VideoMetadata
from ..utils import extract_hostname, extract_filecode
from ..interface.logger import logger

class VidaraEngine:
    """
    Controls the sequence of data retrieval steps.
    """
    
    def __init__(self, output_dir: str = ".", debug: bool = False):
        """
        Prepares the core application utilities.

        Args:
            output_dir (str): The destination folder path for saving.
            debug (bool): Indicates developer mode.
        """
        self.client = VidaraClient()
        self.downloader = FFmpegDownloader(output_dir)
        self.debug = debug

    def fetch_video_data(self, url: str) -> VideoMetadata:
        """
        Connects the client to the server to obtain data.

        This function makes sequential calls so the video details
        can be fetched completely.

        Args:
            url (str): The target user link.

        Returns:
            VideoMetadata: Returns the neatly formatted video information.
        """
        hostname = extract_hostname(url)
        filecode = extract_filecode(url)
        
        logger.info(f"Establishing session cookies for {hostname}...")
        self.client.fetch_initial_cookies(url, hostname, debug=self.debug)
        
        logger.info("Fetching stream metadata via POST request...")
        raw_data = self.client.fetch_stream_metadata(url, hostname, filecode, debug=self.debug)
        
        return VideoMetadata.from_dict(raw_data)

    def process_download(self, metadata: VideoMetadata) -> str:
        """
        Executes the download process based on initial data.

        This function feeds the recording tool with the correct link
        so it is saved to the user's computer.

        Args:
            metadata (VideoMetadata): The collection of source video information.

        Returns:
            str: Returns the file location path of the video.
        """
        title = metadata.title or metadata.filecode
        logger.info(f"Preparing to download: {title}")
        return self.downloader.download_hls(metadata.streaming_url, title)
