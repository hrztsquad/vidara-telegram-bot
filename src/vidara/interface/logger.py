"""
Handles the application's activity history on the console.

This module presents informative text so the process appears
professional and well-organized.
"""

import logging
from rich.logging import RichHandler
from rich.console import Console

console = Console()

def setup_logger(debug_mode: bool = False) -> logging.Logger:
    """
    Sets up the application's activity reporting facility.

    This function beautifies the history to be reader-friendly and
    makes it easier to find the source of issues.

    Args:
        debug_mode (bool): Determines whether detailed info is displayed.

    Returns:
        logging.Logger: Returns the customized activity reporter.
    """
    level = logging.DEBUG if debug_mode else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console, 
                rich_tracebacks=True, 
                show_path=debug_mode,
                markup=True,
            )
        ]
    )
    
    logger = logging.getLogger("vidara")
    
    if not debug_mode:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        
    return logger

logger = logging.getLogger("vidara")
