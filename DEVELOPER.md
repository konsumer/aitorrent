# Developer Guide

This guide explains how to set up the development environment, contribute to the project, and publish new versions.

## Prerequisites

- Python 3.10 or higher
- pip, hatchling (for building), and twine (for manual publishing)
- Git

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/konsumer/aitorrent.git
   cd aitorrent
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Project Structure

- `plexinfo.py`: Plex integration module with both CLI and MCP server functionality
- `tmdbinfo.py`: TMDB integration module with both CLI and MCP server functionality
- `qbtinfo.py`: qBittorrent integration module with both CLI and MCP server functionality
- `pyproject.toml`: Package configuration and dependencies
- `requirements.txt`: Runtime dependencies
- `.env.example`: Example environment configuration

## Development Workflow

### Testing Changes Locally

After making changes to the code, you can test them directly:

```bash
# Test CLI functionality
./plexinfo.py list
./tmdbinfo.py search-shows "Star Trek"
./qbtinfo.py list

# Test MCP servers
aitorrent-plex
aitorrent-tmdb
aitorrent-qbt
```

### Running with Different Methods

You can install and run the package in several ways:

1. **Development install** (recommended for development):
   ```bash
   pip install -e .
   ```

2. **Standard pip install**:
   ```bash
   pip install .
   ```

3. **Using pipx** (recommended for CLI tools):
   ```bash
   pipx install .
   ```

4. **Using uv** (modern, fast alternative):
   ```bash
   uv pip install .
   # Or run without installing:
   uvx --from . aitorrent-plex-cli list
   ```

## Publishing New Versions

### Automated Publishing (Recommended)

This repository is configured with GitHub Actions for automatic publishing to PyPI:

1. Update the version in `pyproject.toml`
2. Create and push a new git tag:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```
3. Create a GitHub Release with the same tag
4. The GitHub Action will automatically publish to PyPI

### Manual Publishing

If needed, you can publish manually:

1. Install build tools:
   ```bash
   pip install build twine
   ```

2. Build the package:
   ```bash
   python -m build
   ```

3. Upload to PyPI:
   ```bash
   twine upload dist/*
   ```

## Environment Variables

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

Required environment variables:
- `PLEX_URL`: Your Plex server URL
- `PLEX_TOKEN`: Your Plex authentication token
- `QBT_URL`: Your qBittorrent Web UI URL
- `QBT_USERNAME`: qBittorrent username (optional if auth is disabled)
- `QBT_PASSWORD`: qBittorrent password (optional if auth is disabled)
- `TMDB_API_KEY`: TMDB API key (optional, for enhanced functionality)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation as needed
6. Submit a pull request

## Code Style

- Follow PEP 8 guidelines
- Use descriptive variable and function names
- Add docstrings to public functions
- Keep functions focused and small
- Comment complex logic

## Questions or Issues

If you have any questions or encounter issues, please open an issue on GitHub.