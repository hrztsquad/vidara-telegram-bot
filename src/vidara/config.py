"""
Manages the application's configuration and environment variables.

This module loads the default settings to ensure the client connection
runs smoothly and optimally.
"""

import os
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = os.getenv(
    "VIDARA_USER_AGENT",
    "Mozilla/5.0 (Linux; Android 14; 2406ERN9CI Build/UKQ1.240116.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.91 Mobile Safari/537.36"
)

API_STREAM_ENDPOINT = os.getenv("VIDARA_API_ENDPOINT", "/api/stream")
DEVICE_TYPE = os.getenv("VIDARA_DEVICE_TYPE", "android")

def get_default_headers(hostname: str = "") -> dict:
    """
    Prepares the HTTP headers for network requests.

    This function sets up the configuration so the client appears
    as a genuine device when accessing the target server.

    Args:
        hostname (str): The target domain name for the headers.

    Returns:
        dict: The prepared header configuration ready for use.
    """
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "id;q=0.9,id-ID;q=0.8,en-US;q=0.7,en;q=0.6",
        "Sec-Fetch-Mode": "navigate",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate",
        "dnt": "1",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": USER_AGENT,
    }
    if hostname:
        headers["Host"] = hostname
    return headers
