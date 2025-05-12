# skt-dl Installation Guide

There are several ways to install the skt-dl package.

## Quick Installation

The easiest way to install skt-dl is directly from GitHub:

```bash
pip install git+https://github.com/example/skt-dl.git
```

## Installation from Source Code

For developers or if you want to modify the code:

```bash
# Clone the repository
git clone https://github.com/example/skt-dl.git
cd skt-dl

# Install in development mode
pip install -e .
```

## Verifying Installation

After installation, you can verify that the package is working correctly:

```bash
# Check version
skt-dl --version

# Show help
skt-dl --help

# Run the package module directly
python -m skt_dl
```

## Running the Web Interface

To start the web interface:

```bash
skt-dl-web
```

This will launch a local web server at http://localhost:5000

## Required Environment Variables

For full functionality, you should set a YouTube API key:

```bash
# Windows
set YOUTUBE_API_KEY=your_api_key_here

# Linux/macOS
export YOUTUBE_API_KEY=your_api_key_here
```

## Common Installation Issues

### Package not found

If you see "Package not found" errors, make sure you have pip installed and that it's up to date:

```bash
pip install --upgrade pip
```

### Missing dependencies

If you encounter missing dependency errors:

```bash
pip install -r requirements.txt
```

### Permission issues

If you encounter permission errors, you can use:

```bash
pip install --user git+https://github.com/example/skt-dl.git
```

### Path issues

If the commands are not found after installation, make sure your Python scripts directory is in your PATH.

## Uninstalling

To uninstall the package:

```bash
pip uninstall skt-dl
```