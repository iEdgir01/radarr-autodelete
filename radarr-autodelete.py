import logging
import os
import sys
import requests
from datetime import datetime
from plexapi.myplex import PlexServer
from plexapi.server import PlexServer as RawPlexServer
from plexapi.exceptions import PlexApiException
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Logging setup
LOG_DIR = '/app/logs'
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, 'radarr_autodelete.log')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s[%(name)s]:%(message)s'))
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s[%(name)s]:%(message)s'))
sys.stdout.flush()
logger.addHandler(stream_handler)

def str_to_bool(var, value):
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    else:
        logger.error(f"Invalid value for {var}: {value}")
        raise ValueError(f"Invalid value for {var}")

RADARR_URL = os.getenv('RADARR_URL')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')
PLEX_USER_TOKEN = os.getenv('PLEX_USER_TOKEN')
ACCEPTED_LANGUAGES = os.getenv('ACCEPTED_LANGUAGES', '').split(',')
COLLECTION_NAME = os.getenv('MOVIE_COLLECTION_NAME')

try:
    LANGUAGE_FILTER = str_to_bool('LANGUAGE_FILTER', os.getenv('LANGUAGE_FILTER', 'false'))
    DRY_RUN = str_to_bool('DRY_RUN', os.getenv('DRY_RUN', 'false'))
    if DRY_RUN:
        logger.setLevel(logging.DEBUG)
except ValueError as e:
    logger.error(str(e))

logger.info('Script started.')
if DRY_RUN:
    logger.info("------ DRY_RUN Mode ------")
    logger.debug(f"LANGUAGE_FILTER: {LANGUAGE_FILTER}")
    logger.debug(f"ACCEPTED_LANGUAGES: {ACCEPTED_LANGUAGES}")
    logger.debug(f"Radarr API URL: {RADARR_URL}")
    logger.debug(f"Radarr API KEY: {RADARR_API_KEY}")
    logger.debug(f"Plex URL: {PLEX_URL}")
    logger.debug(f"Plex TOKEN: {PLEX_TOKEN}")
    logger.debug(f"PLEX_USER_TOKEN: {PLEX_USER_TOKEN}")
    logger.debug(f"Collection Name: {COLLECTION_NAME}")
    logger.debug('--------------------------------------------------')

API_EXTENSION = '/api/v3/'
API_HOST = urljoin(RADARR_URL, API_EXTENSION)
logger.info(f'API URL: {API_HOST}')
MOVIE = []

@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=60),
       retry=retry_if_exception_type((requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, PlexApiException)))
def get(endpoint: str, extra_params: dict):
    params = {'apikey': RADARR_API_KEY}
    params.update(extra_params)
    response = requests.get(API_HOST + endpoint, params=params)
    response.raise_for_status()
    return response.json()

def delete(endpoint: str, extra_params: dict):
    if DRY_RUN:
        logger.debug(f'Dry run: Would delete endpoint {endpoint} with params {extra_params}')
    else:
        params = {'apikey': RADARR_API_KEY}
        params.update(extra_params)
        response = requests.delete(API_HOST + endpoint, params=params)
        response.raise_for_status()

@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=60),
       retry=retry_if_exception_type((requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, PlexApiException)))
def connect_to_plex(plex_url, plex_token):
    return PlexServer(plex_url, plex_token)

try:
    logger.info('Checking Plex service reachability...')
    plex = connect_to_plex(PLEX_URL, PLEX_TOKEN)
    logger.info('Plex service is reachable.')

    logger.info('Checking Radarr service reachability...')
    movies = get('movie', {})
    logger.info('Radarr service is reachable.')

    watched_movies = {}
    logger.info("Checking Plex for watched movies...")

    if PLEX_USER_TOKEN:
        raw_server = RawPlexServer(PLEX_URL, PLEX_TOKEN)
        account = raw_server.myPlexAccount()
        user = account.account()
        user_id = user.id

        sessions = account.resources()
        server = next((s for s in sessions if s.name == raw_server.friendlyName), None)
        history_url = f"https://plex.tv/api/v2/user/{user_id}/history"
        headers = {'X-Plex-Token': PLEX_USER_TOKEN}
        params = {'type': 'movie', 'sort': 'viewedAt:desc', 'limit': 10000}
        response = requests.get(history_url, headers=headers, params=params)
        response.raise_for_status()
        history = response.json()

        for item in history:
            title = item['metadata']['title']
            viewed_at = datetime.fromtimestamp(item['viewedAt'])
            if title not in watched_movies or viewed_at > watched_movies[title]:
                watched_movies[title] = viewed_at
    else:
        movies_section = plex.library.section('Movies')
        for video in movies_section.all():
            if video.isWatched and video.lastViewedAt:
                watched_movies[video.title] = video.lastViewedAt

    logger.info(f"Found {len(watched_movies)} watched movies.")

    for movie in movies:
        title = movie.get("title")
        monitored = movie.get("monitored", True)
        radarr_added = movie.get("added")

        if monitored and title in watched_movies and radarr_added:
            try:
                added_dt = datetime.strptime(radarr_added, "%Y-%m-%dT%H:%M:%SZ")
                viewed_dt = watched_movies[title]

                if viewed_dt > added_dt:
                    if DRY_RUN:
                        logger.debug(f"Dry run: Would unmonitor {title} — watched {viewed_dt} after added {added_dt}")
                    else:
                        movie['monitored'] = False
                        update_url = f'movie/{movie["id"]}'
                        response = requests.put(
                            urljoin(API_HOST, update_url),
                            params={'apikey': RADARR_API_KEY},
                            json=movie
                        )
                        response.raise_for_status()
                        logger.info(f"Unmonitored movie: {title}")
            except Exception as e:
                logger.warning(f"Failed to process movie '{title}' for unmonitoring: {e}")

    movies_section = plex.library.section('Movies')
    for video in movies_section.search(collection=COLLECTION_NAME):
        MOVIE.append(video.title)

    for movie in movies:
        language = movie.get("originalLanguage", {}).get("name", "Unknown")
        monitored = movie.get("monitored", True)

        if movie["title"] not in MOVIE:
            if not monitored:
                if DRY_RUN:
                    logger.debug(f"Dry run: Would remove movie: {movie['title']} - reason: unmonitored")
                else:
                    logger.info(f'Removing movie: {movie["title"]} - reason: unmonitored')
                    delete(f'movie/{movie["id"]}', {'deleteFiles': True, 'addImportExclusion': False})
            elif LANGUAGE_FILTER and language not in ACCEPTED_LANGUAGES:
                if DRY_RUN:
                    logger.debug(f"Dry run: Would remove movie: {movie['title']} - language not accepted ({language})")
                else:
                    logger.info(f"Removing movie: {movie['title']} - language not accepted")
                    delete(f'movie/{movie["id"]}', {'deleteFiles': True, 'addImportExclusion': False})

    for movie in MOVIE:
        logger.info(f"Skipping movie: {movie} - in collection '{COLLECTION_NAME}'")

except Exception as e:
    logger.error(f'An error occurred: {str(e)}')

finally:
    logger.info('Script ended.')