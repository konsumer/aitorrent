#!/usr/bin/env python3
"""
TMDB information tool - can be used as CLI or MCP server.
Retrieves TV show and movie information from The Movie Database (TMDB).
"""

import sys
import argparse
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

try:
    from tmdbv3api import TMDb, TV, Season as TMDbSeason, Movie

    TMDB_AVAILABLE = True
except ImportError:
    TMDB_AVAILABLE = False


class TmdbInfo:
    """Core TMDB information class."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize TMDB connection."""
        if not TMDB_AVAILABLE:
            raise ImportError("tmdbv3api not installed. Run: pip install tmdbv3api")

        self.api_key = api_key or os.getenv("TMDB_API_KEY")
        if not self.api_key:
            raise ValueError("TMDB_API_KEY not found in environment variables")

        self.tmdb = TMDb()
        self.tmdb.api_key = self.api_key
        self.tmdb.language = "en"
        self.tmdb_tv = TV()
        self.tmdb_season = TMDbSeason()
        self.tmdb_movie = Movie()

    def search_shows(self, query: str) -> List[Dict[str, Any]]:
        """Search TMDB for TV shows."""
        try:
            results = self.tmdb_tv.search(query)
            shows = []

            # Handle results - might be list or generator
            result_list = list(results)[:20]  # Convert to list first, then slice

            for show in result_list:
                try:
                    # Safely extract year
                    year = None
                    if hasattr(show, "first_air_date"):
                        first_air_date = getattr(show, "first_air_date", None)
                        if first_air_date:
                            first_air_str = str(first_air_date)
                            if len(first_air_str) >= 4:
                                year = first_air_str[:4]

                    shows.append(
                        {
                            "tmdb_id": getattr(show, "id", None),
                            "name": getattr(show, "name", "Unknown"),
                            "year": year,
                            "overview": getattr(show, "overview", None),
                            "popularity": getattr(show, "popularity", 0),
                            "vote_average": getattr(show, "vote_average", None),
                        }
                    )
                except Exception as item_error:
                    # Skip items that fail to parse
                    continue

            return shows

        except Exception as e:
            import traceback

            traceback.print_exc()
            return [{"error": f"Error searching TMDB: {str(e)}"}]

    def get_show_details(self, tmdb_id: int) -> Dict[str, Any]:
        """Get detailed information about a TV show including all seasons and episodes."""
        try:
            show = self.tmdb_tv.details(tmdb_id)

            # Safely extract year
            year = None
            if hasattr(show, "first_air_date") and show.first_air_date:
                first_air = str(show.first_air_date)
                year = first_air[:4] if len(first_air) >= 4 else None

            # Get all seasons with episode info
            seasons = []
            for season_data in show.seasons:
                if season_data["season_number"] == 0:  # Skip specials
                    continue

                season_details = self.tmdb_season.details(
                    tmdb_id, season_data["season_number"]
                )

                episodes = []
                for ep in season_details.episodes:
                    episodes.append(
                        {
                            "episode_number": ep["episode_number"],
                            "name": ep["name"],
                            "air_date": ep.get("air_date"),
                            "overview": ep.get("overview"),
                        }
                    )

                seasons.append(
                    {
                        "season_number": season_data["season_number"],
                        "name": season_data["name"],
                        "episode_count": season_data["episode_count"],
                        "air_date": season_data.get("air_date"),
                        "episodes": episodes,
                    }
                )

            return {
                "tmdb_id": show.id,
                "name": show.name,
                "year": year,
                "overview": show.overview,
                "status": show.status if hasattr(show, "status") else None,
                "number_of_seasons": show.number_of_seasons,
                "number_of_episodes": show.number_of_episodes,
                "genres": [g["name"] for g in show.genres]
                if hasattr(show, "genres")
                else [],
                "seasons": seasons,
            }

        except Exception as e:
            return {"error": f"Error getting show details: {str(e)}"}

    def get_season_details(self, tmdb_id: int, season_number: int) -> Dict[str, Any]:
        """Get detailed information about a specific season."""
        try:
            season = self.tmdb_season.details(tmdb_id, season_number)

            episodes = []
            for ep in season.episodes:
                episodes.append(
                    {
                        "episode_number": ep["episode_number"],
                        "name": ep["name"],
                        "air_date": ep.get("air_date"),
                        "overview": ep.get("overview"),
                        "still_path": ep.get("still_path"),
                    }
                )

            return {
                "tmdb_id": tmdb_id,
                "season_number": season_number,
                "name": season.name,
                "overview": season.overview if hasattr(season, "overview") else None,
                "air_date": season.air_date if hasattr(season, "air_date") else None,
                "episode_count": len(episodes),
                "episodes": episodes,
            }

        except Exception as e:
            return {"error": f"Error getting season details: {str(e)}"}

    def search_movies(self, query: str) -> List[Dict[str, Any]]:
        """Search TMDB for movies."""
        try:
            results = self.tmdb_movie.search(query)
            movies = []

            for movie in results[:20]:  # Top 20 results
                # Safely extract year
                year = None
                if hasattr(movie, "release_date") and movie.release_date:
                    release = str(movie.release_date)
                    year = release[:4] if len(release) >= 4 else None

                movies.append(
                    {
                        "tmdb_id": movie.id,
                        "title": movie.title,
                        "year": year,
                        "overview": movie.overview
                        if hasattr(movie, "overview")
                        else None,
                        "popularity": movie.popularity
                        if hasattr(movie, "popularity")
                        else 0,
                        "vote_average": movie.vote_average
                        if hasattr(movie, "vote_average")
                        else None,
                    }
                )

            return movies

        except Exception as e:
            return [{"error": f"Error searching movies: {str(e)}"}]

    def get_movie_details(self, tmdb_id: int) -> Dict[str, Any]:
        """Get detailed information about a movie."""
        try:
            movie = self.tmdb_movie.details(tmdb_id)

            # Safely extract year
            year = None
            if hasattr(movie, "release_date") and movie.release_date:
                release = str(movie.release_date)
                year = release[:4] if len(release) >= 4 else None

            return {
                "tmdb_id": movie.id,
                "title": movie.title,
                "year": year,
                "overview": movie.overview,
                "runtime": movie.runtime if hasattr(movie, "runtime") else None,
                "release_date": str(movie.release_date)
                if hasattr(movie, "release_date")
                else None,
                "genres": [g["name"] for g in movie.genres]
                if hasattr(movie, "genres")
                else [],
                "vote_average": movie.vote_average
                if hasattr(movie, "vote_average")
                else None,
                "budget": movie.budget if hasattr(movie, "budget") else None,
                "revenue": movie.revenue if hasattr(movie, "revenue") else None,
            }

        except Exception as e:
            return {"error": f"Error getting movie details: {str(e)}"}


def format_show_list(shows: List[Dict[str, Any]]) -> str:
    """Format show list for display."""
    if not shows:
        return "No shows found.\n"

    if isinstance(shows, list) and len(shows) > 0 and "error" in shows[0]:
        return f"Error: {shows[0]['error']}\n"

    lines = ["Search Results:", ""]
    for show in shows:
        year_str = f" ({show['year']})" if show.get("year") else ""
        lines.append(f"• {show['name']}{year_str}")
        lines.append(f"  TMDB ID: {show['tmdb_id']}")
        if show.get("vote_average"):
            lines.append(f"  Rating: {show['vote_average']}/10")
        if show.get("overview"):
            overview = (
                show["overview"][:150] + "..."
                if len(show["overview"]) > 150
                else show["overview"]
            )
            lines.append(f"  {overview}")
        lines.append("")

    return "\n".join(lines)


def cli_main():
    """CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Query The Movie Database (TMDB) for TV shows and movies"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Search shows
    search_shows = subparsers.add_parser("search-shows", help="Search for TV shows")
    search_shows.add_argument("query", help="Search query")

    # Show details
    show_details = subparsers.add_parser(
        "show-details", help="Get detailed show information"
    )
    show_details.add_argument("tmdb_id", type=int, help="TMDB show ID")

    # Season details
    season_details = subparsers.add_parser(
        "season-details", help="Get season information"
    )
    season_details.add_argument("tmdb_id", type=int, help="TMDB show ID")
    season_details.add_argument("season", type=int, help="Season number")

    # Search movies
    search_movies = subparsers.add_parser("search-movies", help="Search for movies")
    search_movies.add_argument("query", help="Search query")

    # Movie details
    movie_details = subparsers.add_parser(
        "movie-details", help="Get detailed movie information"
    )
    movie_details.add_argument("tmdb_id", type=int, help="TMDB movie ID")

    parser.add_argument("--api-key", help="TMDB API key (or set TMDB_API_KEY env var)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        tmdb = TmdbInfo(api_key=args.api_key)

        if args.command == "search-shows":
            results = tmdb.search_shows(args.query)
            print(format_show_list(results))

        elif args.command == "show-details":
            import json

            result = tmdb.get_show_details(args.tmdb_id)
            print(json.dumps(result, indent=2))

        elif args.command == "season-details":
            import json

            result = tmdb.get_season_details(args.tmdb_id, args.season)
            print(json.dumps(result, indent=2))

        elif args.command == "search-movies":
            results = tmdb.search_movies(args.query)
            print(format_show_list(results))

        elif args.command == "movie-details":
            import json

            result = tmdb.get_movie_details(args.tmdb_id)
            print(json.dumps(result, indent=2))

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

    server = Server("tmdb-info")
    tmdb_info = None

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available MCP tools."""
        return [
            types.Tool(
                name="tmdb_search_shows",
                description="Search The Movie Database for TV shows by name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for the TV show",
                        }
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="tmdb_get_show_details",
                description="Get detailed information about a TV show including all seasons and episodes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tmdb_id": {"type": "integer", "description": "TMDB show ID"}
                    },
                    "required": ["tmdb_id"],
                },
            ),
            types.Tool(
                name="tmdb_get_season_details",
                description="Get detailed information about a specific season of a show",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tmdb_id": {"type": "integer", "description": "TMDB show ID"},
                        "season_number": {
                            "type": "integer",
                            "description": "Season number",
                        },
                    },
                    "required": ["tmdb_id", "season_number"],
                },
            ),
            types.Tool(
                name="tmdb_search_movies",
                description="Search The Movie Database for movies by title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for the movie",
                        }
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="tmdb_get_movie_details",
                description="Get detailed information about a movie",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tmdb_id": {"type": "integer", "description": "TMDB movie ID"}
                    },
                    "required": ["tmdb_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle MCP tool calls."""
        nonlocal tmdb_info

        # Initialize TmdbInfo if not already done
        if tmdb_info is None:
            try:
                tmdb_info = TmdbInfo()
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

        try:
            if name == "tmdb_search_shows":
                if not arguments or "query" not in arguments:
                    return [
                        types.TextContent(
                            type="text", text="Error: query argument required"
                        )
                    ]

                data = tmdb_info.search_shows(arguments["query"])
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "tmdb_get_show_details":
                if not arguments or "tmdb_id" not in arguments:
                    return [
                        types.TextContent(
                            type="text", text="Error: tmdb_id argument required"
                        )
                    ]

                data = tmdb_info.get_show_details(arguments["tmdb_id"])
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "tmdb_get_season_details":
                if (
                    not arguments
                    or "tmdb_id" not in arguments
                    or "season_number" not in arguments
                ):
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: tmdb_id and season_number arguments required",
                        )
                    ]

                data = tmdb_info.get_season_details(
                    arguments["tmdb_id"], arguments["season_number"]
                )
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "tmdb_search_movies":
                if not arguments or "query" not in arguments:
                    return [
                        types.TextContent(
                            type="text", text="Error: query argument required"
                        )
                    ]

                data = tmdb_info.search_movies(arguments["query"])
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "tmdb_get_movie_details":
                if not arguments or "tmdb_id" not in arguments:
                    return [
                        types.TextContent(
                            type="text", text="Error: tmdb_id argument required"
                        )
                    ]

                data = tmdb_info.get_movie_details(arguments["tmdb_id"])
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def run_server():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="tmdb-info",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(run_server())


if __name__ == "__main__":
    # Check if running as MCP server (stdio mode)
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        mcp_main()
    else:
        cli_main()
