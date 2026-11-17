"""
Handles the media stream download process.

This module interacts with system utilities to capture
the broadcast and save it to the device.
"""

import os
import ffmpeg
from ..utils import sanitize_filename
from ..exceptions import DownloadError

class FFmpegDownloader:
    """
    Executes the download process using an external tool.
    """
    def __init__(self, output_dir: str = "."):
        """
        Sets up the file storage directory.

        Args:
            output_dir (str): The destination folder path.
        """
        self.output_dir = output_dir

    def download_hls(self, stream_url: str, title: str) -> str:
        """
        Copies the media stream into a local format.

        This function configures the recording command so the process
        runs smoothly and cleanly.

        Args:
            stream_url (str): The source media link.
            title (str): The original broadcast title.

        Returns:
            str: Returns the absolute path of the downloaded file.

        Raises:
            DownloadError: If a failure occurs during recording.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
        filename = f"{sanitize_filename(title)}.mp4"
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            stream = ffmpeg.input(stream_url)
            stream = ffmpeg.output(stream, output_path, c='copy', loglevel='warning')
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, overwrite_output=True)
            return output_path
        except ffmpeg.Error as e:
            err_msg = e.stderr.decode('utf8', errors='ignore') if e.stderr else str(e)
            raise DownloadError(f"FFmpeg Error: {err_msg}")
