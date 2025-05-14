import yt_dlp
import json
import logging
import random
from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)

# Initialize YTMusic. It can be initialized without authentication for searching.
ytmusic = None
try:
    # Initialize with a language to potentially get more consistent results
    # Also, YTMusic can accept a requests_session for proxying
    # For now, direct initialization. Proxy will be handled by yt-dlp if ytmusicapi fails.
    ytmusic = YTMusic(language='en_US') 
except Exception as e:
    logger.error(f"Failed to initialize YTMusic: {e}")

# User-Agent list (can be shared or moved to a config file)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def _parse_duration_str_to_seconds(duration_str):
    """Converts MM:SS or HH:MM:SS string to seconds."""
    if not duration_str or not isinstance(duration_str, str):
        return 0
    parts = list(map(int, duration_str.split(":")))
    if len(parts) == 2: # MM:SS
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3: # HH:MM:SS
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def search_youtube_music(query, max_results=5, proxy_config=None):
    """
    Searches YouTube Music for tracks based on the query, trying YTMusicAPI first, then yt-dlp.

    Args:
        query (str): The search query (track name, artist, lyrics).
        max_results (int): Maximum number of search results to return.
        proxy_config (str, optional): Proxy URL (e.g., "http://user:pass@host:port"). Defaults to None.

    Returns:
        list: A list of dictionaries, each containing info about a found track
              (id, title, artist, duration, thumbnail_url, url). Returns empty list on error.
    """
    results = []
    logger.info(f"Starting search for query: \'{query}\' with max_results: {max_results}, proxy: {proxy_config}")

    # Attempt 1: Use ytmusicapi
    if ytmusic:
        try:
            logger.info(f"Attempting search with YTMusicAPI for query: \'{query}\'")
            # YTMusicAPI search can take 'songs', 'videos', 'albums', 'artists', 'playlists'
            search_items = ytmusic.search(query=query, filter='songs', limit=max_results)
            if not search_items: # Fallback to videos if no songs found by ytmusicapi
                logger.info(f"No songs found by YTMusicAPI, trying filter=\'videos\' for query: \'{query}\'")
                search_items = ytmusic.search(query=query, filter='videos', limit=max_results)

            if search_items:
                logger.info(f"YTMusicAPI found {len(search_items)} potential results.")
                for item in search_items:
                    if len(results) >= max_results:
                        break
                    try:
                        video_id = item.get('videoId')
                        title = item.get('title')
                        artists_info = item.get('artists')
                        artist_str = "Unknown Artist"
                        if artists_info and isinstance(artists_info, list):
                            artist_str = ', '.join([artist['name'] for artist in artists_info if 'name' in artist])
                        elif item.get('artist'): # yt-dlp like structure sometimes
                             artist_str = item.get('artist') if isinstance(item.get('artist'), str) else item.get('artist')[0]['name']
                        
                        duration_seconds = item.get('duration_seconds') # YTMusicAPI provides this directly for songs
                        if not duration_seconds and item.get('duration'): # For videos, it might be a string MM:SS
                            duration_seconds = _parse_duration_str_to_seconds(item.get('duration'))

                        thumbnail_url = None
                        if item.get('thumbnails') and isinstance(item['thumbnails'], list) and len(item['thumbnails']) > 0:
                            thumbnail_url = item['thumbnails'][-1]['url'] # Get the highest quality thumbnail

                        if video_id and title:
                            results.append({
                                'id': video_id,
                                'title': title,
                                'artist': artist_str,
                                'duration': duration_seconds if duration_seconds else 0,
                                'thumbnail_url': thumbnail_url,
                                'url': f"https://music.youtube.com/watch?v={video_id}"
                            })
                        else:
                            logger.warning(f"Skipping YTMusicAPI item due to missing id/title: {item}")
                    except Exception as item_exc:
                        logger.error(f"Error processing YTMusicAPI item: {item_exc} - Item: {item}", exc_info=True)
            else:
                logger.info(f"YTMusicAPI returned no results for query: \'{query}\'")

        except Exception as e:
            logger.error(f"Error during YTMusicAPI search for query \'{query}\': {e}", exc_info=True)
            # Do not return, proceed to yt-dlp fallback

    # Attempt 2: Fallback to yt-dlp if ytmusicapi fails or yields no results
    if not results: # Only run yt-dlp if ytmusicapi didn't provide results
        logger.info(f"YTMusicAPI did not yield results or failed. Falling back to yt-dlp search for query: \'{query}\'")
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist', # Get basic metadata, 'in_playlist' is safer than True for searches
            'forcejson': True,
            'source_address': '0.0.0.0', # Bind to all interfaces, useful in some environments
            'geo_bypass': True,
            'http_headers': {'User-Agent': random.choice(USER_AGENTS)},
            # 'verbose': True, # Uncomment for debugging
        }
        if proxy_config:
            ydl_opts['proxy'] = proxy_config
            logger.info(f"Using proxy for yt-dlp search: {proxy_config}")

        # yt-dlp search query format: "ytsearch<N>:<query>" or "ytmsearch<N>:<query>"
        # Using ytsearch as it's more general and sometimes ytmsearch has issues.
        search_query_with_prefix = f"ytsearch{max_results}:{query}"
        logger.info(f"Executing yt-dlp search with query: {search_query_with_prefix}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_result_json = ydl.extract_info(search_query_with_prefix, download=False)
                
                if search_result_json and 'entries' in search_result_json:
                    logger.info(f"yt-dlp found {len(search_result_json['entries'])} potential results.")
                    for entry in search_result_json['entries']:
                        if len(results) >= max_results:
                            break
                        if entry and entry.get('id') and entry.get('title') and entry.get('duration'):
                            artist = entry.get('channel') or entry.get('uploader') or "Unknown Artist"
                            title_entry = entry.get('title')

                            # Basic artist/title refinement (often in "Artist - Title" or "Title - Artist" format)
                            # This is a heuristic and might need adjustment.
                            if ' - ' in title_entry:
                                parts = title_entry.split(' - ', 1)
                                # A simple heuristic: if one part seems like the channel/uploader, the other is the title.
                                if len(parts) == 2:
                                    if (entry.get('channel') and parts[0].strip().lower() == entry.get('channel').lower()) or \
                                       (entry.get('uploader') and parts[0].strip().lower() == entry.get('uploader').lower()):
                                        artist = parts[0].strip()
                                        title_entry = parts[1].strip()
                                    elif (entry.get('channel') and parts[1].strip().lower() == entry.get('channel').lower()) or \
                                         (entry.get('uploader') and parts[1].strip().lower() == entry.get('uploader').lower()):
                                        artist = parts[1].strip()
                                        title_entry = parts[0].strip()
                            
                            results.append({
                                'id': entry.get('id'),
                                'title': title_entry,
                                'artist': artist,
                                'duration': entry.get('duration'), # Already in seconds from yt-dlp
                                'thumbnail_url': entry.get('thumbnail'),
                                'url': f"https://music.youtube.com/watch?v={entry.get('id')}" # or entry.get('webpage_url')
                            })
                        else:
                            logger.warning(f"Skipping yt-dlp entry due to missing fields: id={entry.get('id')}, title={entry.get('title')}, duration={entry.get('duration')}")
                else:
                    logger.info(f"No 'entries' found in yt-dlp search result for query: {query}")

        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"yt-dlp search DownloadError for query \'{query}\': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during yt-dlp search for query \'{query}\': {e}", exc_info=True)

    if not results:
        logger.warning(f"Search for \'{query}\' yielded no results from any method.")
    else:
        logger.info(f"Search for \'{query}\' completed. Returning {len(results)} results.")
    return results

# Example usage (for testing - can be run standalone)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Test without proxy
    # search_query = "Imagine Dragons Believer"
    # print(f"Testing search for: {search_query}")
    # found_tracks = search_youtube_music(search_query, max_results=3)
    # print(json.dumps(found_tracks, indent=2))

    # search_query_lyrics = "Is this the real life? Is this just fantasy?"
    # print(f"\nTesting search for lyrics: {search_query_lyrics}")
    # found_tracks_lyrics = search_youtube_music(search_query_lyrics, max_results=1)
    # print(json.dumps(found_tracks_lyrics, indent=2))

    # Test with a proxy (replace with a working proxy if you have one)
    # PROXY = "http://your_proxy_ip:your_proxy_port" # or with auth: "http://user:pass@host:port"
    # search_query_proxy = "Alan Walker Faded"
    # print(f"\nTesting search with proxy ({PROXY}) for: {search_query_proxy}")
    # found_tracks_proxy = search_youtube_music(search_query_proxy, max_results=2, proxy_config=PROXY)
    # print(json.dumps(found_tracks_proxy, indent=2))

    search_query_unicode = "米津玄師 Lemon"
    print(f"\nTesting search for unicode: {search_query_unicode}")
    found_tracks_unicode = search_youtube_music(search_query_unicode, max_results=2)
    print(json.dumps(found_tracks_unicode, indent=2, ensure_ascii=False))

