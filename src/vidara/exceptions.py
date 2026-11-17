"""
Provides a list of custom errors for the application.

These classes help catch and manage issues gracefully
while the application is running.
"""

class VidaraError(Exception):
    """
    Handles general application issues.
    """
    pass

class NetworkError(VidaraError):
    """
    Handles issues when failing to connect to the server.
    """
    pass

class MetadataError(VidaraError):
    """
    Handles issues when failing to parse video information.
    """
    pass

class DownloadError(VidaraError):
    """
    Handles issues when failing to save media data.
    """
    pass
