"""
Handles network communication with the target server.

This module manages sessions and exchanges data with the API
securely and seamlessly.
"""

import json
import requests
from typing import Dict, Any

from ..config import get_default_headers, API_STREAM_ENDPOINT, DEVICE_TYPE
from ..exceptions import NetworkError, MetadataError
from ..interface.logger import logger

class VidaraClient:
    """
    Performs connection processes and network data retrieval.
    """
    def __init__(self):
        """
        Prepares the HTTP session for a new client.
        """
        self.session = requests.Session()

    def fetch_initial_cookies(self, video_url: str, hostname: str, debug: bool = False) -> None:
        """
        Saves temporary cookies from the initial page.

        This function makes the first visit to the server
        to obtain permission for subsequent sessions.

        Args:
            video_url (str): The target video link.
            hostname (str): The domain name from the link.
            debug (bool): Indicates developer mode.

        Raises:
            NetworkError: If it fails to reach the initial page.
        """
        headers = get_default_headers(hostname)
        self.session.headers.update(headers)
        
        try:
            response = self.session.get(video_url, timeout=15)
            response.raise_for_status()
            logger.debug(f"Cookies gathered: {self.session.cookies.get_dict()}")
        except requests.RequestException as e:
            raise NetworkError(f"Failed to fetch initial page: {e}")

    def fetch_stream_metadata(self, video_url: str, hostname: str, filecode: str, debug: bool = False) -> Dict[str, Any]:
        """
        Pulls detailed information from the destination API.

        This function sends the necessary authorization data
        to obtain the playback source.

        Args:
            video_url (str): The target video link.
            hostname (str): The domain name from the link.
            filecode (str): The unique video code.
            debug (bool): Indicates developer mode.

        Returns:
            dict: Returns the collection of response data.

        Raises:
            NetworkError: If communication with the API fails.
            MetadataError: If the response is not formatted correctly.
        """
        payload = {
            "filecode": filecode,
            "device": DEVICE_TYPE
        }
        
        cookie_string = "; ".join([f"{k}={v}" for k, v in self.session.cookies.get_dict().items()])
        json_payload = json.dumps(payload)

        self.session.headers.update({
            "Content-Length": str(len(json_payload)),
            "Content-Type": "application/json",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Cookie": cookie_string,
            "Sec-Fetch-Dest": "empty",
            "Accept": "*/*",
            "Referer": video_url,
            "Origin": f"https://{hostname}",
        })

        logger.debug(f"Prepared Headers: {json.dumps(dict(self.session.headers), indent=2)}")
        logger.debug(f"Prepared Payload: {json_payload}")

        api_url = f"https://{hostname}{API_STREAM_ENDPOINT}"
        
        try:
            response = self.session.post(api_url, json=payload, timeout=15)
            logger.debug(f"API Response Text: {response.text}")
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            err_details = getattr(e.response, 'text', str(e))
            raise NetworkError(f"API Request Failed: {err_details}")
        except ValueError:
            raise MetadataError("Invalid JSON response from API.")

        if 'streaming_url' not in data:
            raise MetadataError("streaming_url not found in the API response.")

        return data
