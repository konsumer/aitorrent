#!/usr/bin/env python3
"""
Plex information tool - can be used as CLI or MCP server.
Retrieves collection and media information from Plex.
"""

import sys
import argparse
from typing import Optional, List, Dict, Any
from plexapi.server import PlexServer
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

try:
    from tmdbv3api import TMDb, TV, Movie, Season
    TMDB_AVAILABLE = True
except ImportError:
    TMDB_AVAILABLE = False


def format_relative_time(dt) -> str:
    """Format a datetime as relative time (e.g., '2 days ago')."""
    if dt is None:
        return "unknown"

    # Ensure dt is a datetime object
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return "unknown"

    # Make sure both datetimes are timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


class PlexInfo:
    """Core Plex information retrieval class."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, tmdb_api_key: Optional[str] = None):
        """Initialize Plex connection and optionally TMDB."""
        self.base_url = base_url or os.getenv('PLEX_URL')
        self.token = token or os.getenv('PLEX_TOKEN')

        if not self.base_url or not self.token:
            raise ValueError(
                "Plex URL and token required. Set PLEX_URL and PLEX_TOKEN "
                "environment variables or pass them as arguments."
            )

        self.plex = PlexServer(self.base_url, self.token)

        # Initialize TMDB if available and configured
        self.tmdb = None
        self.tmdb_tv = None
        self.tmdb_movie = None
        self.tmdb_season = None

        if TMDB_AVAILABLE:
            api_key = tmdb_api_key or os.getenv('TMDB_API_KEY')
            if api_key:
                self.tmdb = TMDb()
                self.tmdb.api_key = api_key
                self.tmdb.language = 'en'
                self.tmdb_tv = TV()
                self.tmdb_movie = Movie()
                self.tmdb_season = Season()

    def get_libraries(self) -> List[Dict[str, str]]:
        """Get all library/collection names and their types."""
        libraries = []
        for section in self.plex.library.sections():
            # Get library locations (can have multiple)
            locations = [loc for loc in section.locations] if hasattr(section, 'locations') else []

            libraries.append({
                'name': section.title,
                'type': section.type,
                'key': section.key,
                'locations': locations
            })
        return libraries

    def get_library_content(self, library_name: str) -> Dict[str, Any]:
        """Get content from a specific library based on its type."""
        try:
            section = self.plex.library.section(library_name)
        except Exception as e:
            raise ValueError(f"Library '{library_name}' not found: {e}")

        library_type = section.type

        if library_type == 'show':
            return self._get_tv_shows(section)
        elif library_type == 'movie':
            return self._get_movies(section)
        elif library_type == 'artist':
            return self._get_music(section)
        else:
            return {
                'library': library_name,
                'type': library_type,
                'error': f"Unsupported library type: {library_type}"
            }

    def search_media(self, query: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Search for media by title across all libraries or in a specific library."""
        results = {
            'query': query,
            'movies': [],
            'shows': [],
            'artists': [],
            'albums': []
        }

        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = self.plex.library.sections()

        for section in sections:
            search_results = section.search(query)
            for item in search_results:
                item_type = item.type

                if item_type == 'movie':
                    results['movies'].append({
                        'title': item.title,
                        'year': getattr(item, 'year', None),
                        'rating': getattr(item, 'rating', None),
                        'summary': getattr(item, 'summary', None),
                        'library': section.title
                    })
                elif item_type == 'show':
                    results['shows'].append({
                        'title': item.title,
                        'year': getattr(item, 'year', None),
                        'rating': getattr(item, 'rating', None),
                        'summary': getattr(item, 'summary', None),
                        'library': section.title
                    })
                elif item_type == 'artist':
                    results['artists'].append({
                        'name': item.title,
                        'summary': getattr(item, 'summary', None),
                        'library': section.title
                    })
                elif item_type == 'album':
                    results['albums'].append({
                        'title': item.title,
                        'artist': item.parentTitle if hasattr(item, 'parentTitle') else None,
                        'year': getattr(item, 'year', None),
                        'library': section.title
                    })

        return results

    def get_show_details(self, title: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific TV show."""
        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = [s for s in self.plex.library.sections() if s.type == 'show']

        for section in sections:
            results = section.search(title)
            for show in results:
                if show.type == 'show' and show.title.lower() == title.lower():
                    show_info = {
                        'title': show.title,
                        'year': getattr(show, 'year', None),
                        'rating': getattr(show, 'rating', None),
                        'contentRating': getattr(show, 'contentRating', None),
                        'summary': getattr(show, 'summary', None),
                        'studio': getattr(show, 'studio', None),
                        'genres': [g.tag for g in getattr(show, 'genres', [])],
                        'library': section.title,
                        'total_seasons': 0,
                        'total_episodes': 0,
                        'seasons': []
                    }

                    for season in show.seasons():
                        episodes = season.episodes()
                        season_info = {
                            'number': season.seasonNumber,
                            'title': season.title,
                            'episode_count': len(episodes),
                            'episodes': []
                        }

                        for episode in episodes:
                            season_info['episodes'].append({
                                'number': episode.episodeNumber,
                                'title': episode.title,
                                'summary': getattr(episode, 'summary', None),
                                'rating': getattr(episode, 'rating', None),
                                'originally_available_at': str(episode.originallyAvailableAt) if hasattr(episode, 'originallyAvailableAt') and episode.originallyAvailableAt else None
                            })

                        show_info['seasons'].append(season_info)
                        show_info['total_episodes'] += len(episodes)

                    show_info['total_seasons'] = len(show_info['seasons'])
                    return show_info

        return {'error': f"Show '{title}' not found"}

    def get_movie_details(self, title: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific movie."""
        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = [s for s in self.plex.library.sections() if s.type == 'movie']

        for section in sections:
            results = section.search(title)
            for movie in results:
                if movie.type == 'movie' and movie.title.lower() == title.lower():
                    return {
                        'title': movie.title,
                        'year': getattr(movie, 'year', None),
                        'rating': getattr(movie, 'rating', None),
                        'contentRating': getattr(movie, 'contentRating', None),
                        'summary': getattr(movie, 'summary', None),
                        'studio': getattr(movie, 'studio', None),
                        'duration': getattr(movie, 'duration', None),
                        'genres': [g.tag for g in getattr(movie, 'genres', [])],
                        'directors': [d.tag for d in getattr(movie, 'directors', [])],
                        'actors': [a.tag for a in getattr(movie, 'actors', [])][:10],  # Limit to 10 actors
                        'collections': [c.tag for c in getattr(movie, 'collections', [])],
                        'library': section.title
                    }

        return {'error': f"Movie '{title}' not found"}

    def get_artist_details(self, name: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific artist."""
        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = [s for s in self.plex.library.sections() if s.type == 'artist']

        for section in sections:
            results = section.search(name)
            for artist in results:
                if artist.type == 'artist' and artist.title.lower() == name.lower():
                    artist_info = {
                        'name': artist.title,
                        'summary': getattr(artist, 'summary', None),
                        'genres': [g.tag for g in getattr(artist, 'genres', [])],
                        'library': section.title,
                        'total_albums': 0,
                        'total_tracks': 0,
                        'albums': []
                    }

                    for album in artist.albums():
                        tracks = album.tracks()
                        album_info = {
                            'title': album.title,
                            'year': getattr(album, 'year', None),
                            'track_count': len(tracks),
                            'tracks': [{'number': t.trackNumber, 'title': t.title} for t in tracks]
                        }
                        artist_info['albums'].append(album_info)
                        artist_info['total_tracks'] += len(tracks)

                    artist_info['total_albums'] = len(artist_info['albums'])
                    return artist_info

        return {'error': f"Artist '{name}' not found"}

    def _get_tv_shows(self, section) -> Dict[str, Any]:
        """Get TV shows with seasons and episodes."""
        shows_data = []
        for show in section.all():
            show_info = {
                'title': show.title,
                'year': getattr(show, 'year', None),
                'seasons': []
            }

            for season in show.seasons():
                season_info = {
                    'number': season.seasonNumber,
                    'title': season.title,
                    'episodes': []
                }

                for episode in season.episodes():
                    season_info['episodes'].append({
                        'number': episode.episodeNumber,
                        'title': episode.title
                    })

                show_info['seasons'].append(season_info)

            shows_data.append(show_info)

        return {
            'library': section.title,
            'type': 'show',
            'count': len(shows_data),
            'shows': shows_data
        }

    def _get_movies(self, section) -> Dict[str, Any]:
        """Get movies grouped by collection."""
        movies_by_collection = {'uncategorized': []}
        all_movies = []
        unique_movies_per_collection = {}

        # Get all movies including external media
        # Use the raw API to ensure we get everything including external media
        key = f'/library/sections/{section.key}/all'
        params = {
            'type': 1,  # movies
            'includeCollections': 1,
            'includeExternalMedia': 1
        }
        items_xml = section._server.query(key, params=params)

        for movie_elem in items_xml:
            movie_info = {
                'title': movie_elem.get('title'),
                'year': int(movie_elem.get('year')) if movie_elem.get('year') else None,
                'collections': []
            }

            # Extract collection tags from XML
            for collection_elem in movie_elem.findall('.//Collection'):
                collection_tag = collection_elem.get('tag')
                if collection_tag:
                    movie_info['collections'].append(collection_tag)
            all_movies.append(movie_info)

            if movie_info['collections']:
                for collection in movie_info['collections']:
                    if collection not in movies_by_collection:
                        movies_by_collection[collection] = []
                        unique_movies_per_collection[collection] = set()

                    movies_by_collection[collection].append({
                        'title': movie_info['title'],
                        'year': movie_info['year']
                    })
                    unique_movies_per_collection[collection].add(movie_info['title'])
            else:
                movies_by_collection['uncategorized'].append({
                    'title': movie_info['title'],
                    'year': movie_info['year']
                })

        # Calculate unique counts for collections
        unique_movies_per_collection['uncategorized'] = set(
            m['title'] for m in movies_by_collection['uncategorized']
        )

        return {
            'library': section.title,
            'type': 'movie',
            'count': len(all_movies),
            'collections': movies_by_collection,
            'unique_counts': {k: len(v) for k, v in unique_movies_per_collection.items()}
        }

    def _get_music(self, section) -> Dict[str, Any]:
        """Get music by artist and album."""
        artists_data = []

        for artist in section.all():
            artist_info = {
                'name': artist.title,
                'albums': []
            }

            for album in artist.albums():
                album_info = {
                    'title': album.title,
                    'year': getattr(album, 'year', None),
                    'tracks': len(album.tracks())
                }
                artist_info['albums'].append(album_info)

            artists_data.append(artist_info)

        return {
            'library': section.title,
            'type': 'artist',
            'count': len(artists_data),
            'artists': artists_data
        }

    def get_on_deck(self) -> Dict[str, Any]:
        """Get items that are currently 'On Deck' (continue watching)."""
        on_deck_items = {
            'shows': [],
            'movies': []
        }

        for item in self.plex.library.onDeck():
            if item.type == 'episode':
                on_deck_items['shows'].append({
                    'show_title': item.grandparentTitle,
                    'season_number': item.seasonNumber,
                    'episode_number': item.episodeNumber,
                    'episode_title': item.title,
                    'summary': getattr(item, 'summary', None),
                    'progress': getattr(item, 'viewOffset', 0),
                    'duration': getattr(item, 'duration', 0)
                })
            elif item.type == 'movie':
                on_deck_items['movies'].append({
                    'title': item.title,
                    'year': getattr(item, 'year', None),
                    'summary': getattr(item, 'summary', None),
                    'progress': getattr(item, 'viewOffset', 0),
                    'duration': getattr(item, 'duration', 0)
                })

        return on_deck_items

    def get_in_progress_shows(self) -> List[Dict[str, Any]]:
        """Get TV shows that have been started but not fully watched."""
        in_progress = []

        for section in self.plex.library.sections():
            if section.type != 'show':
                continue

            for show in section.all():
                watched_count = 0
                total_count = 0
                last_watched_episode = None
                last_viewed_at = None

                for season in show.seasons():
                    # Skip specials (season 0) for progress tracking
                    if season.seasonNumber == 0:
                        continue

                    for episode in season.episodes():
                        total_count += 1
                        if episode.isWatched:
                            watched_count += 1
                            ep_last_viewed = getattr(episode, 'lastViewedAt', None)

                            # Track the most recently watched episode
                            if ep_last_viewed and (last_viewed_at is None or ep_last_viewed > last_viewed_at):
                                last_viewed_at = ep_last_viewed
                                last_watched_episode = {
                                    'season': season.seasonNumber,
                                    'episode': episode.episodeNumber,
                                    'title': episode.title,
                                    'air_date': str(episode.originallyAvailableAt) if hasattr(episode, 'originallyAvailableAt') and episode.originallyAvailableAt else None,
                                    'last_viewed_at': str(ep_last_viewed) if ep_last_viewed else None,
                                    'last_viewed_relative': format_relative_time(ep_last_viewed) if ep_last_viewed else None
                                }

                # Only include shows that are partially watched
                if watched_count > 0 and watched_count < total_count:
                    in_progress.append({
                        'title': show.title,
                        'year': getattr(show, 'year', None),
                        'library': section.title,
                        'watched_episodes': watched_count,
                        'total_episodes': total_count,
                        'completion_percent': round((watched_count / total_count) * 100, 1),
                        'last_watched_episode': last_watched_episode,
                        'last_viewed_at': str(last_viewed_at) if last_viewed_at else None,
                        'last_viewed_relative': format_relative_time(last_viewed_at) if last_viewed_at else None
                    })

        # Sort by most recently watched (strings sort chronologically for ISO format)
        in_progress.sort(key=lambda x: x.get('last_viewed_at') or '', reverse=True)
        return in_progress

    def get_recently_added(self, count: int = 20, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Get recently added items."""
        recent = {
            'shows': [],
            'movies': [],
            'albums': []
        }

        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = self.plex.library.sections()

        for section in sections:
            for item in section.recentlyAdded(maxresults=count):
                added_at = getattr(item, 'addedAt', None)
                if item.type == 'show':
                    recent['shows'].append({
                        'title': item.title,
                        'year': getattr(item, 'year', None),
                        'added_at': str(added_at) if added_at else None,
                        'added_at_dt': added_at,
                        'library': section.title
                    })
                elif item.type == 'movie':
                    recent['movies'].append({
                        'title': item.title,
                        'year': getattr(item, 'year', None),
                        'added_at': str(added_at) if added_at else None,
                        'added_at_dt': added_at,
                        'library': section.title
                    })
                elif item.type == 'album':
                    recent['albums'].append({
                        'title': item.title,
                        'artist': item.parentTitle if hasattr(item, 'parentTitle') else None,
                        'year': getattr(item, 'year', None),
                        'added_at': str(added_at) if added_at else None,
                        'added_at_dt': added_at,
                        'library': section.title
                    })

        return recent

    def get_show_watch_status(self, title: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed watch status for a specific show."""
        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = [s for s in self.plex.library.sections() if s.type == 'show']

        for section in sections:
            results = section.search(title)
            for show in results:
                if show.type == 'show' and show.title.lower() == title.lower():
                    show_info = {
                        'title': show.title,
                        'library': section.title,
                        'total_seasons': 0,
                        'total_episodes': 0,
                        'watched_episodes': 0,
                        'unwatched_episodes': 0,
                        'seasons': []
                    }

                    for season in show.seasons():
                        season_watched = 0
                        season_total = 0
                        episodes_info = []

                        for episode in season.episodes():
                            season_total += 1
                            is_watched = episode.isWatched
                            if is_watched:
                                season_watched += 1
                                show_info['watched_episodes'] += 1
                            else:
                                show_info['unwatched_episodes'] += 1

                            episodes_info.append({
                                'number': episode.episodeNumber,
                                'title': episode.title,
                                'watched': is_watched,
                                'air_date': str(episode.originallyAvailableAt) if hasattr(episode, 'originallyAvailableAt') and episode.originallyAvailableAt else None
                            })

                        show_info['seasons'].append({
                            'number': season.seasonNumber,
                            'title': season.title,
                            'watched': season_watched,
                            'total': season_total,
                            'episodes': episodes_info
                        })

                        show_info['total_episodes'] += season_total

                    show_info['total_seasons'] = len(show_info['seasons'])
                    show_info['completion_percent'] = round((show_info['watched_episodes'] / show_info['total_episodes']) * 100, 1) if show_info['total_episodes'] > 0 else 0

                    return show_info

        return {'error': f"Show '{title}' not found"}

    def find_missing_episodes(self, title: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Find episodes that exist in TMDB but are missing from Plex library."""
        if not self.tmdb:
            return {'error': 'TMDB not configured. Set TMDB_API_KEY environment variable.'}

        # First, get what's in Plex
        plex_status = self.get_show_watch_status(title, library_name)
        if 'error' in plex_status:
            return plex_status

        # Search TMDB for the show
        try:
            search_results = self.tmdb_tv.search(title)
            if not search_results:
                return {'error': f"Show '{title}' not found in TMDB"}

            # Find best match (exact title match or first result)
            tmdb_show = None
            for result in search_results:
                if result.name.lower() == title.lower():
                    tmdb_show = result
                    break
            if not tmdb_show:
                tmdb_show = search_results[0]

            # Get full show details
            show_details = self.tmdb_tv.details(tmdb_show.id)

            # Build list of missing episodes
            missing = {
                'show_title': plex_status['title'],
                'tmdb_id': tmdb_show.id,
                'tmdb_name': show_details.name,
                'year': show_details.first_air_date[:4] if show_details.first_air_date else None,
                'total_seasons_tmdb': show_details.number_of_seasons,
                'total_episodes_tmdb': show_details.number_of_episodes,
                'missing_episodes': []
            }

            # Create a set of episodes we have in Plex
            plex_episodes = set()
            for season in plex_status['seasons']:
                for ep in season['episodes']:
                    plex_episodes.add((season['number'], ep['number']))

            # Check each season in TMDB
            for season_num in range(1, show_details.number_of_seasons + 1):
                try:
                    season_details = self.tmdb_season.details(tmdb_show.id, season_num)

                    for episode in season_details.episodes:
                        ep_key = (season_num, episode.episode_number)

                        # If not in Plex, it's missing
                        if ep_key not in plex_episodes:
                            missing['missing_episodes'].append({
                                'season': season_num,
                                'episode': episode.episode_number,
                                'title': episode.name,
                                'air_date': episode.air_date if episode.air_date else None,
                                'overview': episode.overview if hasattr(episode, 'overview') else None
                            })
                except Exception as e:
                    # Season might not exist or have issues
                    continue

            return missing

        except Exception as e:
            return {'error': f"Error querying TMDB: {str(e)}"}

    def get_next_episodes(self, title: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """Get next unwatched episodes for a show the user is watching."""
        if not self.tmdb:
            return {'error': 'TMDB not configured. Set TMDB_API_KEY environment variable.'}

        # Get watch status from Plex
        plex_status = self.get_show_watch_status(title, library_name)
        if 'error' in plex_status:
            return plex_status

        # Find the last watched episode
        last_watched_season = 0
        last_watched_episode = 0

        for season in plex_status['seasons']:
            for ep in season['episodes']:
                if ep['watched']:
                    if season['number'] > last_watched_season or (
                        season['number'] == last_watched_season and ep['number'] > last_watched_episode
                    ):
                        last_watched_season = season['number']
                        last_watched_episode = ep['number']

        # Search TMDB for new episodes
        try:
            search_results = self.tmdb_tv.search(title)
            if not search_results:
                return {'error': f"Show '{title}' not found in TMDB"}

            tmdb_show = search_results[0]
            show_details = self.tmdb_tv.details(tmdb_show.id)

            next_episodes = {
                'show_title': plex_status['title'],
                'tmdb_id': tmdb_show.id,
                'last_watched': {
                    'season': last_watched_season,
                    'episode': last_watched_episode
                },
                'available_episodes': []
            }

            # Look for episodes after the last watched
            plex_episodes = set()
            for season in plex_status['seasons']:
                for ep in season['episodes']:
                    plex_episodes.add((season['number'], ep['number']))

            # Check seasons starting from last watched
            for season_num in range(last_watched_season, show_details.number_of_seasons + 1):
                try:
                    season_details = self.tmdb_season.details(tmdb_show.id, season_num)

                    for episode in season_details.episodes:
                        # Skip if before last watched
                        if season_num == last_watched_season and episode.episode_number <= last_watched_episode:
                            continue

                        # Check if episode has aired
                        if episode.air_date:
                            air_date = datetime.fromisoformat(episode.air_date)
                            if air_date > datetime.now():
                                # Future episode
                                continue

                        ep_key = (season_num, episode.episode_number)
                        in_plex = ep_key in plex_episodes

                        next_episodes['available_episodes'].append({
                            'season': season_num,
                            'episode': episode.episode_number,
                            'title': episode.name,
                            'air_date': episode.air_date if episode.air_date else None,
                            'in_plex': in_plex,
                            'overview': episode.overview if hasattr(episode, 'overview') else None
                        })
                except Exception:
                    continue

            return next_episodes

        except Exception as e:
            return {'error': f"Error querying TMDB: {str(e)}"}

    def search_tmdb_show(self, query: str) -> List[Dict[str, Any]]:
        """Search TMDB for TV shows."""
        if not self.tmdb:
            return [{'error': 'TMDB not configured. Set TMDB_API_KEY environment variable.'}]

        try:
            results = self.tmdb_tv.search(query)
            shows = []

            for show in results[:10]:  # Limit to top 10 results
                # Safely extract year from first_air_date
                year = None
                if hasattr(show, 'first_air_date') and show.first_air_date:
                    first_air = str(show.first_air_date)
                    year = first_air[:4] if len(first_air) >= 4 else None

                shows.append({
                    'tmdb_id': show.id,
                    'name': show.name,
                    'year': year,
                    'overview': show.overview if hasattr(show, 'overview') else None,
                    'popularity': show.popularity if hasattr(show, 'popularity') else 0
                })

            return shows

        except Exception as e:
            return [{'error': f"Error searching TMDB: {str(e)}"}]

    def format_for_torrent_search(self, show_title: str, season: int, episode: int, year: Optional[int] = None, quality: str = "1080p") -> str:
        """Format show info as a torrent search query."""
        query_parts = [show_title]

        if year:
            query_parts.append(str(year))

        query_parts.append(f"S{season:02d}E{episode:02d}")
        query_parts.append(quality)

        return " ".join(query_parts)

    def get_episodes_to_download(self, show_title: str, quality: str = "1080p", library_name: Optional[str] = None) -> Dict[str, Any]:
        """
        High-level function that returns episodes ready to download.
        Combines finding missing episodes with all the info needed to download them.
        Returns concise, actionable data perfect for automated downloading.
        """
        if not TMDB_AVAILABLE:
            return {'error': 'TMDB integration not available. Install tmdbv3api.'}

        # Get missing episodes
        missing_result = self.find_missing_episodes(show_title, library_name)

        if 'error' in missing_result:
            return missing_result

        if not missing_result.get('missing_episodes'):
            return {
                'show_title': missing_result['show_title'],
                'message': 'No missing episodes',
                'episodes_to_download': []
            }

        # Get show path for downloads
        path_result = self.suggest_download_path(show_title, library_name=library_name)
        base_path = path_result.get('suggested_path', '')

        # Format each episode with all needed info
        episodes = []
        for ep in missing_result['missing_episodes']:
            season = ep['season']
            episode = ep['episode']

            # Season-specific path
            season_path = f"{base_path}/Season {season}" if base_path else None

            # Pre-formatted search query
            search_query = self.format_for_torrent_search(
                show_title=missing_result['show_title'],
                season=season,
                episode=episode,
                year=missing_result.get('year'),
                quality=quality
            )

            episodes.append({
                'season': season,
                'episode': episode,
                'title': ep['title'],
                'air_date': ep['air_date'],
                'search_query': search_query,
                'download_path': season_path
            })

        return {
            'show_title': missing_result['show_title'],
            'year': missing_result.get('year'),
            'library': path_result.get('library'),
            'episodes_to_download': episodes
        }

    def get_show_path(self, title: str, library_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the filesystem path where a show's episodes are stored in Plex.
        Useful for determining where to download new episodes.
        """
        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            sections = [s for s in self.plex.library.sections() if s.type == 'show']

        for section in sections:
            results = section.search(title)
            for show in results:
                if show.type == 'show' and show.title.lower() == title.lower():
                    # Get the path from one of the episodes
                    seasons = show.seasons()
                    if seasons:
                        episodes = seasons[0].episodes()
                        if episodes:
                            # Get the file path of the first episode
                            ep = episodes[0]
                            if hasattr(ep, 'media') and ep.media:
                                media = ep.media[0]
                                if hasattr(media, 'parts') and media.parts:
                                    file_path = media.parts[0].file

                                    # Extract the show directory (parent of season folder)
                                    # Typical structure: /path/to/Show Name/Season 01/Episode.mkv
                                    import re
                                    # Look for pattern like "Season XX" or "S01" or just the show folder
                                    parts = file_path.split('/')

                                    # Find the show directory (usually 2-3 levels up from episode file)
                                    for i in range(len(parts) - 1, -1, -1):
                                        part = parts[i]
                                        # Check if this looks like a season folder
                                        if re.match(r'[Ss]eason\s*\d+|[Ss]\d+', part):
                                            # Show dir is one level up
                                            show_path = '/'.join(parts[:i])
                                            return {
                                                'show_title': show.title,
                                                'show_path': show_path,
                                                'library': section.title,
                                                'library_locations': list(section.locations),
                                                'example_file': file_path
                                            }

                                    # If no season folder pattern found, try 2 levels up from file
                                    if len(parts) >= 3:
                                        show_path = '/'.join(parts[:-2])
                                        return {
                                            'show_title': show.title,
                                            'show_path': show_path,
                                            'library': section.title,
                                            'library_locations': list(section.locations),
                                            'example_file': file_path
                                        }

        return {'error': f"Show '{title}' not found or has no episodes"}

    def suggest_download_path(self, show_title: str, season: Optional[int] = None, library_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggest where to download episodes for a show.
        Checks if show already exists, otherwise suggests path based on library location.
        If season is provided, includes the Season subfolder in the path.
        """
        # First, check if the show already exists in Plex
        existing = self.get_show_path(show_title, library_name)
        if 'show_path' in existing:
            base_path = existing['show_path']
            # Add season folder if season is specified
            if season is not None:
                suggested_path = f"{base_path}/Season {season}"
            else:
                suggested_path = base_path

            return {
                'suggested_path': suggested_path,
                'reason': 'existing_show',
                'show_title': existing['show_title'],
                'library': existing['library'],
                'season': season
            }

        # Show doesn't exist, suggest based on library location
        if library_name:
            try:
                section = self.plex.library.section(library_name)
                sections = [section]
            except Exception as e:
                return {'error': f"Library '{library_name}' not found: {e}"}
        else:
            # Default to first TV show library
            sections = [s for s in self.plex.library.sections() if s.type == 'show']
            if not sections:
                return {'error': 'No TV show libraries found'}

        section = sections[0]
        if not hasattr(section, 'locations') or not section.locations:
            return {'error': f"Library '{section.title}' has no locations configured"}

        # Use the first location
        library_path = section.locations[0]

        # Sanitize show title for filesystem
        import re
        safe_title = re.sub(r'[<>:"/\\|?*]', '', show_title)  # Remove invalid chars
        safe_title = safe_title.strip()

        suggested_path = f"{library_path}/{safe_title}"

        # Add season folder if season is specified
        if season is not None:
            suggested_path = f"{suggested_path}/Season {season}"

        return {
            'suggested_path': suggested_path,
            'reason': 'new_show',
            'show_title': show_title,
            'library': section.title,
            'library_path': library_path,
            'season': season,
            'note': 'This is a new show. Folder will be created on download.'
        }

    def list_library_subdirs(self, library_name: str) -> Dict[str, Any]:
        """
        List all subdirectories in a library's location.
        Useful for LLM to check what show folders already exist.
        """
        try:
            section = self.plex.library.section(library_name)
        except Exception as e:
            return {'error': f"Library '{library_name}' not found: {e}"}

        if not hasattr(section, 'locations') or not section.locations:
            return {'error': f"Library '{library_name}' has no locations configured"}

        library_path = section.locations[0]

        # List directories
        try:
            subdirs = []
            if os.path.exists(library_path):
                for item in os.listdir(library_path):
                    item_path = os.path.join(library_path, item)
                    if os.path.isdir(item_path):
                        subdirs.append(item)

            return {
                'library': library_name,
                'library_path': library_path,
                'subdirectories': sorted(subdirs)
            }
        except Exception as e:
            return {'error': f"Failed to list directory {library_path}: {str(e)}"}


def format_libraries(libraries: List[Dict[str, str]]) -> str:
    """Format library list for display."""
    lines = ["Available Libraries:", ""]
    for lib in libraries:
        lines.append(f"  • {lib['name']} ({lib['type']})")
    return "\n".join(lines)


def format_tv_shows(data: Dict[str, Any]) -> str:
    """Format TV shows for display."""
    lines = [f"TV Shows in '{data['library']}' ({data['count']} shows):", ""]

    for show in data['shows']:
        year_str = f" ({show['year']})" if show['year'] else ""
        lines.append(f"• {show['title']}{year_str}")

        for season in show['seasons']:
            lines.append(f"  └─ Season {season['number']}: {season['title']} ({len(season['episodes'])} episodes)")
            for ep in season['episodes']:
                lines.append(f"     └─ E{ep['number']:02d}: {ep['title']}")
        lines.append("")

    return "\n".join(lines)


def format_movies(data: Dict[str, Any]) -> str:
    """Format movies for display."""
    # Calculate total entries across all collections (may include duplicates)
    total_entries = sum(len(movies) for movies in data['collections'].values())
    unique_note = f" (Note: {total_entries} total entries - some movies in multiple collections)" if total_entries > data['count'] else ""

    lines = [f"Movies in '{data['library']}' ({data['count']} unique movies{unique_note}):", ""]

    for collection, movies in data['collections'].items():
        if movies:
            lines.append(f"• {collection} ({len(movies)} movies)")
            for movie in movies:
                year_str = f" ({movie['year']})" if movie['year'] else ""
                lines.append(f"  └─ {movie['title']}{year_str}")
            lines.append("")

    return "\n".join(lines)


def format_music(data: Dict[str, Any]) -> str:
    """Format music for display."""
    lines = [f"Music in '{data['library']}' ({data['count']} artists):", ""]

    for artist in data['artists']:
        lines.append(f"• {artist['name']}")
        for album in artist['albums']:
            year_str = f" ({album['year']})" if album['year'] else ""
            lines.append(f"  └─ {album['title']}{year_str} - {album['tracks']} tracks")
        lines.append("")

    return "\n".join(lines)


def format_on_deck(data: Dict[str, Any]) -> str:
    """Format on-deck items for display."""
    lines = ["Currently Watching (On Deck):", ""]

    if data['shows']:
        lines.append("TV Shows:")
        for item in data['shows']:
            progress_ms = item['progress']
            duration_ms = item['duration']
            if duration_ms > 0:
                progress_pct = round((progress_ms / duration_ms) * 100, 1)
                lines.append(f"  • {item['show_title']} - S{item['season_number']:02d}E{item['episode_number']:02d}: {item['episode_title']}")
                lines.append(f"    Progress: {progress_pct}%")
            else:
                lines.append(f"  • {item['show_title']} - S{item['season_number']:02d}E{item['episode_number']:02d}: {item['episode_title']}")
        lines.append("")

    if data['movies']:
        lines.append("Movies:")
        for item in data['movies']:
            year_str = f" ({item['year']})" if item['year'] else ""
            progress_ms = item['progress']
            duration_ms = item['duration']
            if duration_ms > 0:
                progress_pct = round((progress_ms / duration_ms) * 100, 1)
                lines.append(f"  • {item['title']}{year_str}")
                lines.append(f"    Progress: {progress_pct}%")
            else:
                lines.append(f"  • {item['title']}{year_str}")
        lines.append("")

    if not data['shows'] and not data['movies']:
        lines.append("  Nothing currently on deck")
        lines.append("")

    return "\n".join(lines)


def format_in_progress_shows(shows: List[Dict[str, Any]]) -> str:
    """Format in-progress shows for display."""
    lines = ["Shows In Progress:", ""]

    if not shows:
        lines.append("  No shows currently being watched")
        lines.append("")
        return "\n".join(lines)

    for show in shows:
        year_str = f" ({show['year']})" if show['year'] else ""
        lines.append(f"• {show['title']}{year_str}")
        lines.append(f"  Progress: {show['watched_episodes']}/{show['total_episodes']} episodes ({show['completion_percent']}%)")

        if show['last_watched_episode']:
            ep = show['last_watched_episode']
            ep_line = f"  Last watched: S{ep['season']:02d}E{ep['episode']:02d} - {ep['title']}"

            # Add relative time if available
            if show.get('last_viewed_at'):
                relative_time = format_relative_time(show['last_viewed_at'])
                ep_line += f" ({relative_time})"

            lines.append(ep_line)

        lines.append("")

    return "\n".join(lines)


def cli_main():
    """CLI entry point."""
    # Load .env file if it exists
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='List Plex media collections and content'
    )
    parser.add_argument(
        'command',
        choices=['list', 'watching'],
        help='Command to execute: "list" to list content, "watching" to show currently watching'
    )
    parser.add_argument(
        'library',
        nargs='?',
        help='Library name (optional for "watching" command)'
    )
    parser.add_argument(
        '--url',
        help='Plex server URL (or set PLEX_URL env var)'
    )
    parser.add_argument(
        '--token',
        help='Plex authentication token (or set PLEX_TOKEN env var)'
    )

    args = parser.parse_args()

    try:
        plex_info = PlexInfo(base_url=args.url, token=args.token)

        if args.command == 'watching':
            # Show watching status
            on_deck = plex_info.get_on_deck()
            in_progress = plex_info.get_in_progress_shows()

            print(format_on_deck(on_deck))
            print(format_in_progress_shows(in_progress))

        elif args.command == 'list':
            if args.library:
                # List content from specific library
                data = plex_info.get_library_content(args.library)

                if 'error' in data:
                    print(f"Error: {data['error']}", file=sys.stderr)
                    sys.exit(1)

                if data['type'] == 'show':
                    print(format_tv_shows(data))
                elif data['type'] == 'movie':
                    print(format_movies(data))
                elif data['type'] == 'artist':
                    print(format_music(data))
            else:
                # List all libraries
                libraries = plex_info.get_libraries()
                print(format_libraries(libraries))

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

    server = Server("plex-info")
    plex_info = None

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available MCP tools."""
        return [
            types.Tool(
                name="plex_list_libraries",
                description="List all Plex libraries/collections with their types",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="plex_list_library_content",
                description="List content from a specific Plex library. Returns TV shows with seasons/episodes, movies by collection, or music by artist/album depending on library type.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "library_name": {
                            "type": "string",
                            "description": "Name of the Plex library to list content from"
                        }
                    },
                    "required": ["library_name"]
                }
            ),
            types.Tool(
                name="plex_search",
                description="Search for media by title across all libraries or in a specific library. Returns matching movies, shows, artists, and albums.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (title or partial title)"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in. If not provided, searches all libraries."
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="plex_get_show_details",
                description="Get detailed information about a specific TV show including all seasons and episodes, with air dates. Useful for determining what episodes exist and when they aired.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact title of the TV show"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="plex_get_movie_details",
                description="Get detailed information about a specific movie including cast, genres, collections, summary, and ratings.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact title of the movie"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="plex_get_artist_details",
                description="Get detailed information about a specific music artist including all albums and tracks.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Exact name of the artist"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["name"]
                }
            ),
            types.Tool(
                name="plex_get_on_deck",
                description="Get items currently 'On Deck' (continue watching). Shows what episodes/movies the user is currently watching or partially through. Excellent for determining what shows someone is actively watching.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="plex_get_in_progress_shows",
                description="Get TV shows that have been started but not fully watched. Shows completion percentage and last watched episode. Perfect for finding shows the user is actively following.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="plex_get_recently_added",
                description="Get recently added items (shows, movies, albums). Useful for seeing what's new in the library.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of items to return (default: 20)"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="plex_get_show_watch_status",
                description="Get detailed watch status for a specific show. Shows which episodes are watched/unwatched per season. Very useful for finding missing episodes or seeing viewing progress.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact title of the TV show"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="plex_find_missing_episodes",
                description="Find episodes that exist in TMDB but are missing from Plex library. Compares TMDB episode list with what's in Plex to identify what needs to be downloaded. Requires TMDB_API_KEY.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact title of the TV show"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="plex_get_next_episodes",
                description="Get next unwatched episodes for a show the user is watching. Shows which episodes are available after the last watched episode, and whether they're in Plex already. Perfect for 'download new episodes' requests. Requires TMDB_API_KEY.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact title of the TV show"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="plex_search_tmdb_show",
                description="Search TMDB for TV shows. Useful when user mentions a show not in their library. Returns TMDB metadata. Requires TMDB_API_KEY.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for the TV show"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="plex_format_torrent_query",
                description="Format show info as a torrent search query string (e.g., 'Star Trek Strange New Worlds 2022 S02E05 1080p'). Use this to prepare queries for torrent searches.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "show_title": {
                            "type": "string",
                            "description": "Title of the TV show"
                        },
                        "season": {
                            "type": "integer",
                            "description": "Season number"
                        },
                        "episode": {
                            "type": "integer",
                            "description": "Episode number"
                        },
                        "year": {
                            "type": "integer",
                            "description": "Optional: Year of the show (helps with disambiguation)"
                        },
                        "quality": {
                            "type": "string",
                            "description": "Optional: Preferred quality (default: 1080p)"
                        }
                    },
                    "required": ["show_title", "season", "episode"]
                }
            ),
            types.Tool(
                name="plex_get_episodes_to_download",
                description="HIGH-LEVEL: Get all episodes that need to be downloaded for a show. Returns missing episodes with pre-formatted search queries and download paths. Perfect for automated daily checks - call this once and get everything you need to download new episodes. Minimizes context usage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "show_title": {
                            "type": "string",
                            "description": "Title of the TV show"
                        },
                        "quality": {
                            "type": "string",
                            "description": "Optional: Preferred quality (default: 1080p)"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library"
                        }
                    },
                    "required": ["show_title"]
                }
            ),
            types.Tool(
                name="plex_get_show_path",
                description="Get the filesystem path where a show's episodes are currently stored in Plex. Returns the actual directory path. Perfect for determining where to download new episodes of existing shows.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Exact title of the TV show"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library to search in"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="plex_suggest_download_path",
                description="Suggest where to download episodes for a show. If the show exists in Plex, returns its current path. If it's a new show, suggests a path based on library location and show name. If season is provided, includes the Season subfolder (e.g., '/path/to/Show/Season 3'). Essential for organizing downloads properly for Plex.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "show_title": {
                            "type": "string",
                            "description": "Title of the TV show"
                        },
                        "season": {
                            "type": "integer",
                            "description": "Optional: Season number to include in path (e.g., 3 for Season 3)"
                        },
                        "library_name": {
                            "type": "string",
                            "description": "Optional: Name of the Plex library (defaults to first TV library)"
                        }
                    },
                    "required": ["show_title"]
                }
            ),
            types.Tool(
                name="plex_list_library_subdirs",
                description="List all subdirectories in a library's filesystem location. Useful for checking what show folders already exist before suggesting new paths or for fuzzy matching show names.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "library_name": {
                            "type": "string",
                            "description": "Name of the Plex library"
                        }
                    },
                    "required": ["library_name"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle MCP tool calls."""
        nonlocal plex_info

        # Initialize PlexInfo if not already done
        if plex_info is None:
            try:
                plex_info = PlexInfo()
            except ValueError as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

        try:
            if name == "plex_list_libraries":
                libraries = plex_info.get_libraries()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(libraries, indent=2)
                )]

            elif name == "plex_list_library_content":
                if not arguments or 'library_name' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: library_name argument required"
                    )]

                data = plex_info.get_library_content(arguments['library_name'])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_search":
                if not arguments or 'query' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: query argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.search_media(arguments['query'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_show_details":
                if not arguments or 'title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: title argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.get_show_details(arguments['title'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_movie_details":
                if not arguments or 'title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: title argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.get_movie_details(arguments['title'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_artist_details":
                if not arguments or 'name' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: name argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.get_artist_details(arguments['name'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_on_deck":
                data = plex_info.get_on_deck()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_in_progress_shows":
                data = plex_info.get_in_progress_shows()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_recently_added":
                count = arguments.get('count', 20) if arguments else 20
                library_name = arguments.get('library_name') if arguments else None
                data = plex_info.get_recently_added(count, library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_show_watch_status":
                if not arguments or 'title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: title argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.get_show_watch_status(arguments['title'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_find_missing_episodes":
                if not arguments or 'title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: title argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.find_missing_episodes(arguments['title'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_next_episodes":
                if not arguments or 'title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: title argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.get_next_episodes(arguments['title'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_search_tmdb_show":
                if not arguments or 'query' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: query argument required"
                    )]

                data = plex_info.search_tmdb_show(arguments['query'])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_format_torrent_query":
                if not arguments or 'show_title' not in arguments or 'season' not in arguments or 'episode' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: show_title, season, and episode arguments required"
                    )]

                query = plex_info.format_for_torrent_search(
                    arguments['show_title'],
                    arguments['season'],
                    arguments['episode'],
                    arguments.get('year'),
                    arguments.get('quality', '1080p')
                )
                return [types.TextContent(
                    type="text",
                    text=query
                )]

            elif name == "plex_get_episodes_to_download":
                if not arguments or 'show_title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: show_title argument required"
                    )]

                data = plex_info.get_episodes_to_download(
                    arguments['show_title'],
                    quality=arguments.get('quality', '1080p'),
                    library_name=arguments.get('library_name')
                )
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_get_show_path":
                if not arguments or 'title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: title argument required"
                    )]

                library_name = arguments.get('library_name')
                data = plex_info.get_show_path(arguments['title'], library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_suggest_download_path":
                if not arguments or 'show_title' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: show_title argument required"
                    )]

                season = arguments.get('season')
                library_name = arguments.get('library_name')
                data = plex_info.suggest_download_path(arguments['show_title'], season, library_name)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(data, indent=2)
                )]

            elif name == "plex_list_library_subdirs":
                if not arguments or 'library_name' not in arguments:
                    return [types.TextContent(
                        type="text",
                        text="Error: library_name argument required"
                    )]

                data = plex_info.list_library_subdirs(arguments['library_name'])
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
                    server_name="plex-info",
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
