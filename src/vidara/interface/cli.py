"""
Handles the interaction between the user and the application.

This module reads terminal commands and renders them with
aesthetic visual components.
"""

import argparse
import sys
from rich.panel import Panel
from rich.table import Table

from .logger import setup_logger, logger, console
from ..core.engine import VidaraEngine
from ..exceptions import VidaraError

def display_banner() -> None:
    """
    Displays the opening greeting on the terminal.

    This function draws a beautiful text block as a welcoming
    message for the user.
    """
    banner_text = (
        "[bold cyan]Vidara CLI Downloader[/bold cyan]\n"
        "[dim]High-performance HLS stream extractor and metadata parser.[/dim]"
    )
    console.print(Panel(banner_text, expand=False, border_style="cyan"))

def display_metadata(metadata) -> None:
    """
    Displays the video information in a table format.

    This function arranges the columns neatly so the video summary
    is easy to read.

    Args:
        metadata (VideoMetadata): The collection of related video information.
    """
    table = Table(title="Video Information", show_header=False, box=None)
    table.add_column("Property", style="cyan", justify="right")
    table.add_column("Value", style="white")
    
    table.add_row("Title:", metadata.title)
    table.add_row("Filecode:", metadata.filecode)
    table.add_row("Subtitles:", metadata.default_sub_lang or "None")
    table.add_row("Thumbnail:", metadata.thumbnail or "None")
    
    console.print(Panel(table, expand=False, border_style="blue"))

def main() -> None:
    """
    Executes the main flow of the terminal application.

    This function absorbs arguments, directs the operation's path,
    and displays interactive indicators as the process runs.
    """
    parser = argparse.ArgumentParser(description="Download videos from Vidara.")
    parser.add_argument("url", nargs="?", help="The Vidara video URL to download.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging (shows headers, payloads, and raw responses).")
    parser.add_argument("--output", "-o", default=".", help="Output directory for the downloaded video.")
    
    args = parser.parse_args()
    
    setup_logger(debug_mode=args.debug)
    
    display_banner()
    
    url = args.url
    if not url:
        url = console.input("[bold yellow]Enter Vidara URL:[/bold yellow] ").strip()
        
    if not url:
        logger.error("URL cannot be empty.")
        sys.exit(1)
        
    engine = VidaraEngine(output_dir=args.output, debug=args.debug)
    
    try:
        with console.status("[bold cyan]Fetching video metadata and handling strict headers...", spinner="dots"):
            metadata = engine.fetch_video_data(url)
            
        display_metadata(metadata)
        
        with console.status("[bold green]Downloading video stream using FFmpeg...", spinner="dots"):
            output_path = engine.process_download(metadata)
            
        logger.info(f"[bold green]Download completed successfully:[/bold green] {output_path}")
            
    except VidaraError as e:
        logger.error(f"Client Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
