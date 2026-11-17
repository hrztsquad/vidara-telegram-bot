#!/usr/bin/env python3
"""
Handles the startup process for the VidaraCLI application.

This script loads the necessary dependencies so the application
can be executed seamlessly via the command line interface.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from vidara.interface.cli import main
except ImportError as e:
    print(f"Error: Missing dependencies or invalid folder structure: {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()
