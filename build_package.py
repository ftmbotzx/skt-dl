#!/usr/bin/env python3
"""
Helper script for building and installing the skt-dl package
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a shell command and print output"""
    print(f"\n=== {description} ===")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Output: {e.output}")
        print(f"Error output: {e.stderr}")
        return False

def clean_build_files():
    """Clean up build files and directories"""
    print("\n=== Cleaning up build files ===")
    directories_to_clean = ['build', 'dist', 'skt_dl.egg-info']
    
    for directory in directories_to_clean:
        path = Path(directory)
        if path.exists():
            print(f"Removing {directory}")
            shutil.rmtree(path)

def build_package():
    """Build the Python package"""
    return run_command("python -m build", "Building package")

def install_package():
    """Install the package in development mode"""
    return run_command("pip install -e .", "Installing package in development mode")

def build_and_install():
    """Build and install the package"""
    clean_build_files()
    if build_package():
        print("\n=== Build successful ===")
        print("\nTo install the package:")
        print("  pip install dist/skt_dl-*.whl")
        
        print("\nTo upload to PyPI (if you have permissions):")
        print("  python -m twine upload dist/*")
        
        return True
    return False

if __name__ == "__main__":
    print("skt-dl Package Builder")
    
    # Check if build module is installed
    try:
        import build
    except ImportError:
        print("\nThe 'build' package is not installed. Installing it now...")
        if not run_command("pip install build", "Installing build package"):
            print("Failed to install 'build' package. Please install it manually:")
            print("  pip install build")
            sys.exit(1)
    
    # Build the package
    if build_and_install():
        print("\nPackage build complete!")
    else:
        print("\nPackage build failed.")
        sys.exit(1)