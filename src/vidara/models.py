"""
Provides the data structure for video information.

This module ensures the metadata layout is always neat
and easily accessible by the application components.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class VideoMetadata:
    """
    Stores detailed information related to the video.
    """
    filecode: str
    title: str
    streaming_url: str
    thumbnail: Optional[str] = None
    default_sub_lang: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VideoMetadata':
        """
        Creates an object from a set of raw data.

        This function filters the data from the server response
        into a well-structured format.

        Args:
            data (dict): The raw data in dictionary format.

        Returns:
            VideoMetadata: Returns the video information object.
        """
        return cls(
            filecode=data.get("filecode", "unknown"),
            title=data.get("title", "Unknown Title"),
            streaming_url=data.get("streaming_url", ""),
            thumbnail=data.get("thumbnail"),
            default_sub_lang=data.get("default_sub_lang")
        )
