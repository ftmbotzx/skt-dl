# skt-dl Deployment Guide

This document provides instructions for building, installing, and deploying the skt-dl package.

## Local Development Installation

To install skt-dl for local development:

```bash
# Clone the repository
git clone https://github.com/example/skt-dl.git
cd skt-dl

# Install in development mode
pip install -e .
```

## Building the Package

To build the distribution packages:

```bash
# Install build dependencies
pip install build wheel

# Build the package
python -m build
```

This will create both source distribution (.tar.gz) and wheel (.whl) packages in the `dist/` directory.

## Testing the Package Locally

To test the built package locally without publishing to PyPI:

```bash
# Install the wheel package directly
pip install dist/skt_dl-*.whl
```

## Publishing to PyPI

To publish the package to PyPI:

1. Create an account on [PyPI](https://pypi.org/)
2. Install the required tools:

```bash
pip install twine
```

3. Upload the package:

```bash
# Test PyPI (recommended for first-time uploads)
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Production PyPI
twine upload dist/*
```

## Installation from PyPI

Once published, users can install your package with:

```bash
# Install from PyPI
pip install skt-dl
```

## Environment Variables

The following environment variables can be set to configure skt-dl:

- `YOUTUBE_API_KEY`: YouTube Data API v3 key for improved reliability
- `SKT_DL_DOWNLOAD_DIR`: Directory to save downloaded files (default: ~/skt-dl-downloads)
- `SESSION_SECRET`: Secret key for Flask sessions in the web interface
- `PORT`: Port for the web server (default: 5000)
- `SKT_DL_PRODUCTION`: Set to "true" to run the web interface in production mode

## Usage After Installation

After installation, the following commands will be available:

```bash
# Show package information
python -m skt_dl

# Run the CLI
skt-dl --help

# Run the web interface
skt-dl-web
```