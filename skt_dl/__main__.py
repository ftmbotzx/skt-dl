#!/usr/bin/env python3
"""
Main module for running skt-dl as a package
"""

import sys
import argparse
from . import __version__
from .cli import main as cli_main
from .web import run_app as web_main
from .constants import PACKAGE_NAME

def show_package_info():
    """
    Display package information
    """
    print(f"{PACKAGE_NAME} version {__version__}")
    print("A custom YouTube video and playlist downloader")
    print()
    print("Available commands:")
    print("  skt-dl        - Run the command-line interface")
    print("  skt-dl-web    - Run the web interface")
    print()
    print("For more information, run:")
    print("  skt-dl --help")
    print("  skt-dl-web --help")

def main():
    """
    Main entry point when running as a module (python -m skt_dl)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description=f"{PACKAGE_NAME} - YouTube Downloader")
    parser.add_argument('--version', '-v', action='store_true', help='Show version information')
    parser.add_argument('--web', '-w', action='store_true', help='Run the web interface')
    
    # If no arguments are provided, show package info
    if len(sys.argv) == 1:
        show_package_info()
        return 0
    
    args = parser.parse_args()
    
    # Show version information
    if args.version:
        print(f"{PACKAGE_NAME} version {__version__}")
        return 0
    
    # Run web interface
    if args.web:
        web_main()  # This starts a web server and doesn't return
        return 0
    
    # Default to CLI mode
    return cli_main()

if __name__ == "__main__":
    exit_code = main()
    if isinstance(exit_code, int):
        sys.exit(exit_code)
    else:
        sys.exit(0)