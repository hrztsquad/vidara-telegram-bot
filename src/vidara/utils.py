"""
Provides utility functions for data manipulation.

This module helps clean up URLs and text formats
before they are processed by other components.
"""

import re
from urllib.parse import urlparse
from .exceptions import MetadataError

def extract_filecode(url: str) -> str:
    """
    Extracts the unique file code from a given link.

    Args:
        url (str): The original video link.

    Returns:
        str: Returns the unique file code.

    Raises:
        MetadataError: If the link does not match the expected format.
    """
    match = re.search(r'/[vde]/([^/?]+)', url)
    if not match:
        raise MetadataError("Invalid URL format. Could not find the file code.")
    return match.group(1)

def extract_hostname(url: str) -> str:
    """
    Extracts the domain name from a given link.

    Args:
        url (str): The original video link.

    Returns:
        str: Returns the domain name.

    Raises:
        MetadataError: If the domain name cannot be found.
    """
    hostname = urlparse(url).hostname
    if not hostname:
        raise MetadataError("The URL does not contain a valid hostname.")
    return hostname

def sanitize_filename(name: str) -> str:
    """
    Cleans up the file name from hazardous characters.

    This function ensures the file name is safe when saved
    into the local storage system.

    Args:
        name (str): The original media title.

    Returns:
        str: Returns a clean and safe file name.
    """
    name = str(name)
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip() or "video"
