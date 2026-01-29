#!/usr/bin/env python3
"""
qBittorrent information tool - can be used as CLI or MCP server.
Manages torrent downloads and RSS automation.
"""

import sys
import argparse
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

try:
    import qbittorrentapi
    QBT_AVAILABLE = True
except ImportError:
    QBT_AVAILABLE = False


class QbtInfo:
    """Core qBittorrent management class."""

    def __init__(self, url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize qBittorrent connection."""
        if not QBT_AVAILABLE:
            raise ImportError("qbittorrent-api not installed. Run: pip install qbittorrent-api")

        # Parse URL (new format) or fall back to old QBT_HOST/QBT_PORT for compatibility
        qbt_url = url or os.getenv('QBT_URL')

        if qbt_url:
            # Parse the URL
            parsed = urlparse(qbt_url)
            self.host = parsed.hostname or 'localhost'
            self.port = parsed.port or 8080
        else:
            # Fall back to old format for backwards compatibility
            self.host = os.getenv('QBT_HOST', 'localhost')
            self.port = int(os.getenv('QBT_PORT', '8080'))

        # Handle empty strings as None for no-auth scenarios
        self.username = username if username is not None else os.getenv('QBT_USERNAME', 'admin')
        self.password = password if password is not None else os.getenv('QBT_PASSWORD', 'adminadmin')

        # If credentials are empty strings, treat as None (no auth)
        if self.username == '':
            self.username = None
        if self.password == '':
            self.password = None

        # Connect to qBittorrent
        self.client = qbittorrentapi.Client(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )

        try:
            self.client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            raise ValueError(f"Failed to login to qBittorrent: {e}")

    def get_torrents(self, filter_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of torrents with optional filter."""
        try:
            if filter_status:
                torrents = self.client.torrents_info(status_filter=filter_status)
            else:
                torrents = self.client.torrents_info()

            torrent_list = []
            for torrent in torrents:
                torrent_list.append({
                    'hash': torrent.hash,
                    'name': torrent.name,
                    'state': torrent.state,
                    'progress': round(torrent.progress * 100, 2),
                    'size': torrent.size,
                    'downloaded': torrent.downloaded,
                    'uploaded': torrent.uploaded,
                    'dlspeed': torrent.dlspeed,
                    'upspeed': torrent.upspeed,
                    'eta': torrent.eta,
                    'category': torrent.category,
                    'save_path': torrent.save_path,
                    'added_on': torrent.added_on,
                    'completion_on': torrent.completion_on
                })

            return torrent_list

        except Exception as e:
            return [{'error': f"Failed to get torrents: {str(e)}"}]

    def get_torrent_details(self, torrent_hash: str) -> Dict[str, Any]:
        """Get detailed information about a specific torrent."""
        try:
            torrent = self.client.torrents_info(torrent_hashes=torrent_hash)
            if not torrent:
                return {'error': f"Torrent {torrent_hash} not found"}

            t = torrent[0]
            return {
                'hash': t.hash,
                'name': t.name,
                'state': t.state,
                'progress': round(t.progress * 100, 2),
                'size': t.size,
                'downloaded': t.downloaded,
                'uploaded': t.uploaded,
                'dlspeed': t.dlspeed,
                'upspeed': t.upspeed,
                'eta': t.eta,
                'ratio': t.ratio,
                'category': t.category,
                'tags': t.tags,
                'save_path': t.save_path,
                'added_on': t.added_on,
                'completion_on': t.completion_on,
                'tracker': t.tracker,
                'num_seeds': t.num_seeds,
                'num_leechs': t.num_leechs
            }

        except Exception as e:
            return {'error': f"Failed to get torrent details: {str(e)}"}

    def add_torrent(self, url_or_magnet: str, save_path: Optional[str] = None,
                   category: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, str]:
        """Add a torrent by URL or magnet link."""
        try:
            result = self.client.torrents_add(
                urls=url_or_magnet,
                save_path=save_path,
                category=category,
                tags=tags
            )

            if result == "Ok.":
                return {
                    'status': 'success',
                    'message': f"Torrent added successfully"
                }
            else:
                return {
                    'status': 'error',
                    'message': f"Failed to add torrent: {result}"
                }

        except Exception as e:
            return {'status': 'error', 'message': f"Error adding torrent: {str(e)}"}

    def pause_torrent(self, torrent_hash: str) -> Dict[str, str]:
        """Pause a torrent."""
        try:
            self.client.torrents_pause(torrent_hashes=torrent_hash)
            return {'status': 'success', 'message': f"Torrent {torrent_hash} paused"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to pause torrent: {str(e)}"}

    def resume_torrent(self, torrent_hash: str) -> Dict[str, str]:
        """Resume a torrent."""
        try:
            self.client.torrents_resume(torrent_hashes=torrent_hash)
            return {'status': 'success', 'message': f"Torrent {torrent_hash} resumed"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to resume torrent: {str(e)}"}

    def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> Dict[str, str]:
        """Delete a torrent, optionally with files."""
        try:
            self.client.torrents_delete(delete_files=delete_files, torrent_hashes=torrent_hash)
            files_msg = " and files" if delete_files else ""
            return {'status': 'success', 'message': f"Torrent{files_msg} deleted"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to delete torrent: {str(e)}"}

    def get_categories(self) -> Dict[str, Any]:
        """Get all categories."""
        try:
            categories = self.client.torrents_categories()
            return {
                'categories': {
                    name: {'save_path': cat.savePath}
                    for name, cat in categories.items()
                }
            }
        except Exception as e:
            return {'error': f"Failed to get categories: {str(e)}"}

    def create_category(self, name: str, save_path: str) -> Dict[str, str]:
        """Create a new category."""
        try:
            self.client.torrents_create_category(name=name, save_path=save_path)
            return {'status': 'success', 'message': f"Category '{name}' created"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to create category: {str(e)}"}

    def get_rss_feeds(self, with_data: bool = False) -> Dict[str, Any]:
        """
        Get all RSS feeds and folders.

        Args:
            with_data: If True, include feed items/articles
        """
        try:
            feeds = self.client.rss_items(with_data=with_data)
            return {'feeds': dict(feeds)}
        except Exception as e:
            return {'error': f"Failed to get RSS feeds: {str(e)}"}

    def add_rss_feed(self, url: str, path: Optional[str] = None) -> Dict[str, str]:
        """
        Add a new RSS feed.

        Args:
            url: RSS feed URL
            path: Optional folder path (e.g., "folder1" or "folder1\\subfolder")
        """
        try:
            item_path = f"{path}\\{url}" if path else url
            self.client.rss_add_feed(url=url, item_path=item_path)
            return {'status': 'success', 'message': f"RSS feed added: {url}"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to add RSS feed: {str(e)}"}

    def remove_rss_feed(self, path: str) -> Dict[str, str]:
        """
        Remove an RSS feed or folder.

        Args:
            path: Path to the feed or folder (e.g., "folder1\\feedname")
        """
        try:
            self.client.rss_remove_item(item_path=path)
            return {'status': 'success', 'message': f"RSS item removed: {path}"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to remove RSS item: {str(e)}"}

    def refresh_rss_feed(self, path: Optional[str] = None) -> Dict[str, str]:
        """
        Refresh RSS feed(s).

        Args:
            path: Optional path to specific feed. If None, refreshes all feeds.
        """
        try:
            if path:
                self.client.rss_refresh_item(item_path=path)
                return {'status': 'success', 'message': f"RSS feed refreshed: {path}"}
            else:
                self.client.rss_refresh_item()
                return {'status': 'success', 'message': "All RSS feeds refreshed"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to refresh RSS feed: {str(e)}"}

    def get_rss_rules(self) -> Dict[str, Any]:
        """Get all RSS auto-download rules."""
        try:
            rules = self.client.rss_rules()
            return {'rules': {name: dict(rule) for name, rule in rules.items()}}
        except Exception as e:
            return {'error': f"Failed to get RSS rules: {str(e)}"}

    def add_rss_rule(self, rule_name: str, rule_def: Dict[str, Any]) -> Dict[str, str]:
        """Add an RSS auto-download rule."""
        try:
            self.client.rss_set_rule(rule_name=rule_name, rule_def=rule_def)
            return {'status': 'success', 'message': f"RSS rule '{rule_name}' created"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to create RSS rule: {str(e)}"}

    def update_rss_rule(self, rule_name: str, rule_def: Dict[str, Any]) -> Dict[str, str]:
        """Update an existing RSS auto-download rule."""
        try:
            self.client.rss_set_rule(rule_name=rule_name, rule_def=rule_def)
            return {'status': 'success', 'message': f"RSS rule '{rule_name}' updated"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to update RSS rule: {str(e)}"}

    def attach_rule_to_feeds(self, rule_name: str, feed_paths: List[str]) -> Dict[str, str]:
        """
        Attach an RSS rule to specific feeds.

        Args:
            rule_name: Name of the RSS rule
            feed_paths: List of feed paths to attach the rule to (e.g., ["folder\\feed1", "feed2"])
        """
        try:
            # Get existing rule
            rules = self.client.rss_rules()
            if rule_name not in rules:
                return {'status': 'error', 'message': f"Rule '{rule_name}' not found"}

            rule_def = dict(rules[rule_name])
            rule_def['affectedFeeds'] = feed_paths

            # Update rule with new feed attachments
            self.client.rss_set_rule(rule_name=rule_name, rule_def=rule_def)
            return {
                'status': 'success',
                'message': f"Rule '{rule_name}' attached to {len(feed_paths)} feed(s)",
                'feeds': feed_paths
            }
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to attach rule to feeds: {str(e)}"}

    def delete_rss_rule(self, rule_name: str) -> Dict[str, str]:
        """Delete an RSS auto-download rule."""
        try:
            self.client.rss_remove_rule(rule_name=rule_name)
            return {'status': 'success', 'message': f"RSS rule '{rule_name}' deleted"}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to delete RSS rule: {str(e)}"}

    def create_show_rss_rule(self, show_name: str, season: Optional[int] = None,
                            quality: str = "1080p", category: Optional[str] = None,
                            save_path: Optional[str] = None,
                            feed_paths: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Create an RSS rule for a TV show that will auto-download new episodes.

        Args:
            show_name: Name of the TV show
            season: Optional season number to filter for (e.g., 2 for S02)
            quality: Quality preference (default: 1080p)
            category: Category to assign downloaded torrents to
            save_path: Path to save downloads
            feed_paths: Optional list of feed paths to attach this rule to (e.g., ["folder\\feed1"])
                       If None or empty, applies to all feeds
        """
        try:
            # Build the filter pattern
            # Example: "Star Trek Strange New Worlds S02.*1080p"
            filter_pattern = show_name.replace(":", "").strip()

            if season:
                filter_pattern += f" S{season:02d}"

            if quality:
                filter_pattern += f".*{quality}"

            rule_def = {
                'enabled': True,
                'mustContain': filter_pattern,
                'mustNotContain': '',
                'useRegex': True,
                'episodeFilter': '',
                'smartFilter': False,
                'previouslyMatchedEpisodes': [],
                'affectedFeeds': feed_paths if feed_paths else [],  # Specific feeds or all feeds
                'ignoreDays': 0,
                'lastMatch': '',
                'addPaused': False,
                'assignedCategory': category or '',
                'savePath': save_path or ''
            }

            rule_name = f"{show_name}"
            if season:
                rule_name += f" S{season:02d}"

            self.client.rss_set_rule(rule_name=rule_name, rule_def=rule_def)

            return {
                'status': 'success',
                'message': f"RSS rule created for {show_name}",
                'rule_name': rule_name,
                'filter_pattern': filter_pattern,
                'attached_feeds': feed_paths if feed_paths else 'all'
            }

        except Exception as e:
            return {'status': 'error', 'message': f"Failed to create show RSS rule: {str(e)}"}

    def get_transfer_info(self) -> Dict[str, Any]:
        """Get transfer speed and total stats."""
        try:
            info = self.client.transfer_info()
            return {
                'dl_info_speed': info.dl_info_speed,
                'dl_info_data': info.dl_info_data,
                'up_info_speed': info.up_info_speed,
                'up_info_data': info.up_info_data,
                'dl_rate_limit': info.dl_rate_limit,
                'up_rate_limit': info.up_rate_limit
            }
        except Exception as e:
            return {'error': f"Failed to get transfer info: {str(e)}"}

    def search_torrents(self, query: str, plugins: str = "all", category: str = "all") -> Dict[str, Any]:
        """
        Search for torrents using qBittorrent's search plugins.

        Args:
            query: Search query string
            plugins: Comma-separated list of plugin names or "all" (default: "all")
            category: Category filter: all, movies, tv, music, etc. (default: "all")
        """
        try:
            # Start search
            search_job = self.client.search_start(pattern=query, plugins=plugins, category=category)

            # Wait for search to get sufficient results (not necessarily complete)
            import time
            max_wait = 15
            for i in range(max_wait):
                time.sleep(1)
                status = self.client.search_status(search_id=search_job.id)
                if status and status[0].status == 'Stopped':
                    break
                # If we have some results and it's been at least 8 seconds, that's enough
                if i >= 7:
                    results_check = self.client.search_results(search_id=search_job.id, limit=1)
                    if isinstance(results_check, dict) and len(results_check.get('results', [])) > 5:
                        break

            # Get final status and results
            status = self.client.search_status(search_id=search_job.id)
            results = self.client.search_results(search_id=search_job.id, limit=100)

            # Delete the search job
            try:
                self.client.search_delete(search_id=search_job.id)
            except:
                pass

            # Parse results - it's a dict with 'results' key containing the actual list
            result_list = []
            if isinstance(results, dict):
                result_list = results.get('results', [])
            else:
                result_list = results

            # Format and filter results
            torrents = []
            for result in result_list:
                if isinstance(result, dict):
                    name = result.get('fileName', 'Unknown')
                    size = result.get('fileSize', 0)
                    seeds = result.get('nbSeeders', 0)
                    leeches = result.get('nbLeechers', 0)
                    url = result.get('fileUrl', '')

                    # Filter out error messages and invalid results
                    if size <= 0 or seeds < 0 or 'error' in name.lower():
                        continue

                    # Filter out non-magnet/torrent URLs (HTML pages from some plugins)
                    if not url:
                        continue

                    # Keep only magnet links or direct .torrent file URLs
                    if not (url.startswith('magnet:?') or url.endswith('.torrent')):
                        continue

                    torrents.append({
                        'name': name,
                        'size': size,
                        'seeds': seeds,
                        'leeches': leeches,
                        'engine_url': url,
                        'desc_link': result.get('descrLink', ''),
                        'site': result.get('siteUrl', ''),
                        'engine': result.get('engineName', '')
                    })

            # Sort by seeders (highest first)
            torrents.sort(key=lambda x: x['seeds'], reverse=True)

            return {
                'query': query,
                'status': status[0].status if status else 'unknown',
                'total_results': status[0].total if status else len(torrents),
                'results': torrents
            }

        except Exception as e:
            return {'error': f"Failed to search torrents: {str(e)}"}

    def get_search_plugins(self) -> Dict[str, Any]:
        """Get list of installed search plugins."""
        try:
            plugins = self.client.search_plugins()
            plugin_list = []
            for plugin in plugins:
                plugin_list.append({
                    'name': plugin.name,
                    'full_name': plugin.fullName,
                    'version': plugin.version,
                    'enabled': plugin.enabled,
                    'url': plugin.url,
                    'supported_categories': plugin.supportedCategories
                })
            return {'plugins': plugin_list}
        except Exception as e:
            return {'error': f"Failed to get search plugins: {str(e)}"}

    def get_downloading_episodes(self, show_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse currently downloading/active torrents to extract episode information.
        Useful for checking what's already being downloaded before searching for new episodes.

        Args:
            show_name: Optional show name to filter by (case-insensitive partial match)
        """
        try:
            import re

            # Get active torrents (downloading, queued, checking, etc.)
            torrents = self.client.torrents_info()

            episodes = []
            for torrent in torrents:
                # Skip completed torrents
                if torrent.state in ['uploading', 'pausedUP', 'stalledUP']:
                    continue

                name = torrent.name

                # Filter by show name if provided
                if show_name and show_name.lower() not in name.lower():
                    continue

                # Try to extract season/episode info (S01E02 or s01e02 format)
                match = re.search(r'[Ss](\d{1,2})[Ee](\d{1,2})', name)
                if match:
                    season = int(match.group(1))
                    episode = int(match.group(2))

                    # Try to extract show name (everything before SxxExx)
                    show_match = re.search(r'^(.+?)[Ss]\d{1,2}[Ee]\d{1,2}', name)
                    extracted_show = show_match.group(1).strip('. -_') if show_match else name

                    episodes.append({
                        'show_name': extracted_show,
                        'season': season,
                        'episode': episode,
                        'torrent_name': name,
                        'state': torrent.state,
                        'progress': round(torrent.progress * 100, 1),
                        'size': torrent.size,
                        'downloaded': torrent.downloaded
                    })

            return {
                'filter': show_name if show_name else 'all',
                'downloading_episodes': episodes,
                'count': len(episodes)
            }

        except Exception as e:
            return {'error': f"Failed to get downloading episodes: {str(e)}"}


def format_bytes(bytes_val: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def format_speed(bytes_per_sec: int) -> str:
    """Format speed as human-readable."""
    return format_bytes(bytes_per_sec) + "/s"


def format_eta(seconds: int) -> str:
    """Format ETA in human-readable time."""
    if seconds < 0 or seconds == 8640000:  # 8640000 = infinity
        return "∞"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_torrents(torrents: List[Dict[str, Any]]) -> str:
    """Format torrent list for display."""
    if not torrents:
        return "No torrents found.\n"

    lines = ["Active Torrents:", ""]

    for t in torrents:
        if 'error' in t:
            lines.append(f"Error: {t['error']}")
            continue

        lines.append(f"• {t['name']}")
        lines.append(f"  Status: {t['state']} - {t['progress']:.1f}%")
        lines.append(f"  Size: {format_bytes(t['size'])} (Downloaded: {format_bytes(t['downloaded'])})")
        lines.append(f"  Speed: ↓ {format_speed(t['dlspeed'])} ↑ {format_speed(t['upspeed'])}")

        if t['eta'] > 0 and t['eta'] != 8640000:
            lines.append(f"  ETA: {format_eta(t['eta'])}")

        if t['category']:
            lines.append(f"  Category: {t['category']}")

        lines.append(f"  Path: {t['save_path']}")
        lines.append("")

    return "\n".join(lines)


def cli_main():
    """CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Manage qBittorrent downloads and automation'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List command
    list_parser = subparsers.add_parser('list', help='List torrents')
    list_parser.add_argument('filter', nargs='?',
                           choices=['all', 'downloading', 'completed', 'active', 'inactive', 'paused'],
                           default='all',
                           help='Filter torrents by status')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a torrent')
    add_parser.add_argument('url', help='Magnet link or torrent URL')
    add_parser.add_argument('--path', help='Save path')
    add_parser.add_argument('--category', help='Category')
    add_parser.add_argument('--tags', help='Comma-separated tags')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for torrents')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--plugins', default='all', help='Plugins to use (default: all)')
    search_parser.add_argument('--category', default='all', help='Category filter (default: all)')

    # RSS command
    rss_parser = subparsers.add_parser('rss', help='Manage RSS feeds and rules')
    rss_subparsers = rss_parser.add_subparsers(dest='rss_command')

    rss_list_feeds = rss_subparsers.add_parser('list-feeds', help='List RSS feeds')
    rss_list_feeds.add_argument('--with-data', action='store_true', help='Include feed items/articles')

    rss_add_feed = rss_subparsers.add_parser('add-feed', help='Add RSS feed')
    rss_add_feed.add_argument('url', help='RSS feed URL')
    rss_add_feed.add_argument('--folder', help='Folder path (e.g., "TV Shows")')

    rss_remove_feed = rss_subparsers.add_parser('remove-feed', help='Remove RSS feed or folder')
    rss_remove_feed.add_argument('path', help='Path to feed or folder')

    rss_refresh = rss_subparsers.add_parser('refresh', help='Refresh RSS feeds')
    rss_refresh.add_argument('--path', help='Optional: specific feed path to refresh')

    rss_list_rules = rss_subparsers.add_parser('list-rules', help='List RSS rules')

    rss_add_show = rss_subparsers.add_parser('add-show', help='Add RSS rule for a show')
    rss_add_show.add_argument('show_name', help='Name of the show')
    rss_add_show.add_argument('--season', type=int, help='Season number')
    rss_add_show.add_argument('--quality', default='1080p', help='Quality (default: 1080p)')
    rss_add_show.add_argument('--category', help='Category')
    rss_add_show.add_argument('--path', help='Save path')
    rss_add_show.add_argument('--feeds', help='Comma-separated feed paths to attach rule to')

    rss_attach = rss_subparsers.add_parser('attach-rule', help='Attach rule to feeds')
    rss_attach.add_argument('rule_name', help='Name of the rule')
    rss_attach.add_argument('feeds', help='Comma-separated feed paths')

    # Connection args
    parser.add_argument('--url', help='qBittorrent URL (e.g. http://localhost:8080) or set QBT_URL env var')
    parser.add_argument('--username', help='qBittorrent username (or set QBT_USERNAME env var)')
    parser.add_argument('--password', help='qBittorrent password (or set QBT_PASSWORD env var)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        qbt = QbtInfo(
            url=args.url,
            username=args.username,
            password=args.password
        )

        if args.command == 'list':
            filter_status = None if args.filter == 'all' else args.filter
            torrents = qbt.get_torrents(filter_status=filter_status)
            print(format_torrents(torrents))

        elif args.command == 'add':
            tags = args.tags.split(',') if args.tags else None
            result = qbt.add_torrent(
                args.url,
                save_path=args.path,
                category=args.category,
                tags=tags
            )
            print(f"{result['status'].upper()}: {result['message']}")

        elif args.command == 'search':
            result = qbt.search_torrents(
                args.query,
                plugins=args.plugins,
                category=args.category
            )
            if 'error' in result:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)

            print(f"Search results for: {result['query']}")
            print(f"Status: {result['status']}, Total: {result['total_results']}")
            print("")

            if not result['results']:
                print("No results found.")
            else:
                for i, torrent in enumerate(result['results'][:20], 1):
                    print(f"{i}. {torrent['name']}")
                    print(f"   Size: {format_bytes(torrent['size'])} | Seeds: {torrent['seeds']} | Leeches: {torrent['leeches']}")
                    print(f"   URL: {torrent['engine_url']}")
                    print("")

        elif args.command == 'rss':
            if args.rss_command == 'list-feeds':
                feeds = qbt.get_rss_feeds(with_data=args.with_data)
                if 'error' in feeds:
                    print(f"Error: {feeds['error']}", file=sys.stderr)
                    sys.exit(1)

                print("RSS Feeds:", "")
                if not feeds['feeds']:
                    print("  No feeds configured")
                else:
                    import json
                    print(json.dumps(feeds['feeds'], indent=2))

            elif args.rss_command == 'add-feed':
                result = qbt.add_rss_feed(args.url, path=args.folder)
                print(f"{result['status'].upper()}: {result['message']}")

            elif args.rss_command == 'remove-feed':
                result = qbt.remove_rss_feed(args.path)
                print(f"{result['status'].upper()}: {result['message']}")

            elif args.rss_command == 'refresh':
                result = qbt.refresh_rss_feed(path=args.path)
                print(f"{result['status'].upper()}: {result['message']}")

            elif args.rss_command == 'list-rules':
                rules = qbt.get_rss_rules()
                if 'error' in rules:
                    print(f"Error: {rules['error']}", file=sys.stderr)
                    sys.exit(1)

                print("RSS Auto-Download Rules:", "")
                if not rules['rules']:
                    print("  No rules configured")
                else:
                    for name, rule in rules['rules'].items():
                        print(f"• {name}")
                        if 'mustContain' in rule:
                            print(f"  Filter: {rule['mustContain']}")
                        if 'assignedCategory' in rule and rule['assignedCategory']:
                            print(f"  Category: {rule['assignedCategory']}")
                        if 'affectedFeeds' in rule and rule['affectedFeeds']:
                            print(f"  Attached to: {', '.join(rule['affectedFeeds'])}")
                        print("")

            elif args.rss_command == 'add-show':
                feed_paths = args.feeds.split(',') if args.feeds else None
                result = qbt.create_show_rss_rule(
                    args.show_name,
                    season=args.season,
                    quality=args.quality,
                    category=args.category,
                    save_path=args.path,
                    feed_paths=feed_paths
                )
                print(f"{result['status'].upper()}: {result['message']}")
                if result['status'] == 'success':
                    print(f"Rule name: {result['rule_name']}")
                    print(f"Filter pattern: {result['filter_pattern']}")
                    print(f"Attached to feeds: {result['attached_feeds']}")

            elif args.rss_command == 'attach-rule':
                feed_paths = args.feeds.split(',')
                result = qbt.attach_rule_to_feeds(args.rule_name, feed_paths)
                print(f"{result['status'].upper()}: {result['message']}")
                if result['status'] == 'success':
                    print(f"Feeds: {', '.join(result['feeds'])}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


# MCP Server implementation
def mcp_main():
    """MCP server entry point."""
    import asyncio
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types
    import json

    server = Server("qbt-info")
    qbt = None

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available MCP tools."""
        return [
            types.Tool(
                name="qbt_get_torrents",
                description="Get list of torrents with optional status filter (all, downloading, completed, active, inactive, paused)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter_status": {
                            "type": "string",
                            "enum": ["all", "downloading", "completed", "active", "inactive", "paused"],
                            "description": "Filter torrents by status"
                        }
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_get_torrent_details",
                description="Get detailed information about a specific torrent by hash",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "torrent_hash": {
                            "type": "string",
                            "description": "Hash of the torrent"
                        }
                    },
                    "required": ["torrent_hash"]
                }
            ),
            types.Tool(
                name="qbt_add_torrent",
                description="Add a torrent by magnet link or URL. Can optionally specify save path, category, and tags.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url_or_magnet": {
                            "type": "string",
                            "description": "Magnet link or torrent URL"
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Optional: Path to save downloaded files"
                        },
                        "category": {
                            "type": "string",
                            "description": "Optional: Category name"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional: List of tags"
                        }
                    },
                    "required": ["url_or_magnet"]
                }
            ),
            types.Tool(
                name="qbt_get_categories",
                description="Get all torrent categories with their save paths",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_create_category",
                description="Create a new category with save path",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Category name"
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Path where torrents in this category will be saved"
                        }
                    },
                    "required": ["name", "save_path"]
                }
            ),
            types.Tool(
                name="qbt_get_rss_feeds",
                description="Get all RSS feeds and folders. Use this to see what RSS feeds are configured before attaching rules to them.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "with_data": {
                            "type": "boolean",
                            "description": "Include feed items/articles in response (default: false)"
                        }
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_add_rss_feed",
                description="Add a new RSS feed URL to qBittorrent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "RSS feed URL"
                        },
                        "path": {
                            "type": "string",
                            "description": "Optional folder path (e.g., 'TV Shows' or 'TV Shows\\Sci-Fi')"
                        }
                    },
                    "required": ["url"]
                }
            ),
            types.Tool(
                name="qbt_remove_rss_feed",
                description="Remove an RSS feed or folder",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the feed or folder (e.g., 'TV Shows\\feedname')"
                        }
                    },
                    "required": ["path"]
                }
            ),
            types.Tool(
                name="qbt_refresh_rss_feed",
                description="Manually refresh RSS feed(s) to check for new items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Optional path to specific feed. If not provided, refreshes all feeds."
                        }
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_get_rss_rules",
                description="Get all RSS auto-download rules. Shows which rules exist and what feeds they're attached to.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_attach_rule_to_feeds",
                description="Attach an existing RSS rule to specific feeds. This is CRITICAL - rules won't trigger unless attached to feeds!",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_name": {
                            "type": "string",
                            "description": "Name of the RSS rule"
                        },
                        "feed_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of feed paths to attach the rule to (e.g., ['TV Shows\\ShowRSS', 'folder\\feed2'])"
                        }
                    },
                    "required": ["rule_name", "feed_paths"]
                }
            ),
            types.Tool(
                name="qbt_create_show_rss_rule",
                description="Create an RSS rule to auto-download new episodes of a TV show. Perfect for 'automatically download new episodes' requests. IMPORTANT: You should attach the rule to specific feeds using feed_paths, otherwise it may not trigger!",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "show_name": {
                            "type": "string",
                            "description": "Name of the TV show"
                        },
                        "season": {
                            "type": "integer",
                            "description": "Optional: Season number to filter for"
                        },
                        "quality": {
                            "type": "string",
                            "description": "Quality preference (e.g., 1080p, 720p, 2160p). Default: 1080p"
                        },
                        "category": {
                            "type": "string",
                            "description": "Optional: Category to assign downloads to"
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Optional: Path to save downloads"
                        },
                        "feed_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional: List of feed paths to attach this rule to (e.g., ['TV Shows\\ShowRSS']). If not provided, applies to all feeds."
                        }
                    },
                    "required": ["show_name"]
                }
            ),
            types.Tool(
                name="qbt_delete_rss_rule",
                description="Delete an RSS auto-download rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_name": {
                            "type": "string",
                            "description": "Name of the RSS rule to delete"
                        }
                    },
                    "required": ["rule_name"]
                }
            ),
            types.Tool(
                name="qbt_get_transfer_info",
                description="Get current transfer speeds and total transfer stats",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_search_torrents",
                description="Search for torrents using qBittorrent's installed search plugins. Returns torrent results with name, size, seeders, leechers, and download links.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'Star Trek Strange New Worlds S01E10 1080p')"
                        },
                        "plugins": {
                            "type": "string",
                            "description": "Plugin names to use, comma-separated or 'all' (default: 'all')"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category filter: all, movies, tv, music, etc. (default: 'all')"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="qbt_get_search_plugins",
                description="Get list of installed search plugins in qBittorrent. Shows which plugins are available and enabled for searching.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="qbt_get_downloading_episodes",
                description="HIGH-LEVEL: Get currently downloading/active episodes parsed from torrent names. Perfect for checking what's already being downloaded before searching for new episodes. Filters out completed torrents. Minimizes duplicate downloads.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "show_name": {
                            "type": "string",
                            "description": "Optional: Filter by show name (case-insensitive partial match)"
                        }
                    },
                    "required": []
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle MCP tool calls."""
        nonlocal qbt

        # Initialize QbtInfo if not already done
        if qbt is None:
            try:
                qbt = QbtInfo()
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

        try:
            if name == "qbt_get_torrents":
                filter_status = arguments.get('filter_status') if arguments else None
                if filter_status == 'all':
                    filter_status = None
                data = qbt.get_torrents(filter_status=filter_status)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_get_torrent_details":
                if not arguments or 'torrent_hash' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: torrent_hash argument required"
                    )]

                data = qbt.get_torrent_details(arguments['torrent_hash'])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_add_torrent":
                if not arguments or 'url_or_magnet' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: url_or_magnet argument required"
                    )]

                result = qbt.add_torrent(
                    arguments['url_or_magnet'],
                    save_path=arguments.get('save_path'),
                    category=arguments.get('category'),
                    tags=arguments.get('tags')
                )
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_get_categories":
                data = qbt.get_categories()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_create_category":
                if not arguments or 'name' not in arguments or 'save_path' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: name and save_path arguments required"
                    )]

                result = qbt.create_category(arguments['name'], arguments['save_path'])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_get_rss_feeds":
                with_data = arguments.get('with_data', False) if arguments else False
                data = qbt.get_rss_feeds(with_data=with_data)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_add_rss_feed":
                if not arguments or 'url' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: url argument required"
                    )]

                result = qbt.add_rss_feed(
                    arguments['url'],
                    path=arguments.get('path')
                )
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_remove_rss_feed":
                if not arguments or 'path' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: path argument required"
                    )]

                result = qbt.remove_rss_feed(arguments['path'])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_refresh_rss_feed":
                path = arguments.get('path') if arguments else None
                result = qbt.refresh_rss_feed(path=path)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_get_rss_rules":
                data = qbt.get_rss_rules()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_attach_rule_to_feeds":
                if not arguments or 'rule_name' not in arguments or 'feed_paths' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: rule_name and feed_paths arguments required"
                    )]

                result = qbt.attach_rule_to_feeds(
                    arguments['rule_name'],
                    arguments['feed_paths']
                )
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_create_show_rss_rule":
                if not arguments or 'show_name' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: show_name argument required"
                    )]

                result = qbt.create_show_rss_rule(
                    arguments['show_name'],
                    season=arguments.get('season'),
                    quality=arguments.get('quality', '1080p'),
                    category=arguments.get('category'),
                    save_path=arguments.get('save_path'),
                    feed_paths=arguments.get('feed_paths')
                )
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_delete_rss_rule":
                if not arguments or 'rule_name' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: rule_name argument required"
                    )]

                result = qbt.delete_rss_rule(arguments['rule_name'])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "qbt_get_transfer_info":
                data = qbt.get_transfer_info()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_search_torrents":
                if not arguments or 'query' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: query argument required"
                    )]

                plugins = arguments.get('plugins', 'all')
                category = arguments.get('category', 'all')
                data = qbt.search_torrents(arguments['query'], plugins, category)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_get_search_plugins":
                data = qbt.get_search_plugins()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "qbt_get_downloading_episodes":
                show_name = arguments.get('show_name') if arguments else None
                data = qbt.get_downloading_episodes(show_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            else:
                return [types.TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def run_server():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="qbt-info",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    )
                )
            )

    asyncio.run(run_server())


if __name__ == '__main__':
    # Check if running as MCP server (stdio mode)
    if len(sys.argv) > 1 and sys.argv[1] == 'mcp':
        mcp_main()
    else:
        cli_main()
