
import logging
import os
import sys
import requests
from datetime import datetime
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi.exceptions import PlexApiException
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --------------------------
# Configuration
# --------------------------
PLEX_USERNAME = os.getenv('PLEX_USERNAME')
PLEX_PASSWORD = os.getenv('PLEX_PASSWORD')
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')

RADARR_URL = os.getenv('RADARR_URL')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')

ACCEPTED_LANGUAGES = os.getenv('ACCEPTED_LANGUAGES', '').split(',')
MOVIE_COLLECTION_NAME = os.getenv('MOVIE_COLLECTION_NAME')
LANGUAGE_FILTER = False
DRY_RUN = True  # Set to False to actually perform deletions/unmonitoring

# --------------------------
# Logging setup
# --------------------------
LOG_DIR = '/app/logs'
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, 'radarr_autodelete.log')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger.addHandler(stream_handler)

if DRY_RUN:
    logger.setLevel(logging.DEBUG)
    logger.debug("====== DRY_RUN Mode Enabled ======")

logger.info("====== Script Started ======")

# --------------------------
# Helper functions
# --------------------------
def str_to_bool(var, value):
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    else:
        logger.error(f"Invalid value for {var}: {value}")
        raise ValueError(f"Invalid value for {var}")

API_EXTENSION = '/api/v3/'
API_HOST = urljoin(RADARR_URL, API_EXTENSION)
MOVIE_COLLECTION = []

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
        logger.debug(f"Dry run: Would delete endpoint {endpoint} with params {extra_params}")
    else:
        params = {'apikey': RADARR_API_KEY}
        params.update(extra_params)
        response = requests.delete(API_HOST + endpoint, params=params)
        response.raise_for_status()

@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=60),
       retry=retry_if_exception_type((requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError, PlexApiException)))
def connect_to_plex(plex_url, plex_token):
    return PlexServer(plex_url, plex_token)

# --------------------------
# Main script
# --------------------------
try:
    logger.info("------ Signing in to Plex account ------")
    plex_account = MyPlexAccount(PLEX_USERNAME, PLEX_PASSWORD)
    PLEX_USER_TOKEN = plex_account.authToken
    logger.info(f"Signed in as {plex_account.username}, user token obtained")

    logger.info("------ Connecting to Plex server ------")
    plex = connect_to_plex(PLEX_URL, PLEX_TOKEN)
    logger.info(f"Connected to Plex server: {plex.friendlyName}")

    logger.info("------ Checking Radarr service ------")
    movies = get('movie', {})
    logger.info("Radarr service is reachable.")

    logger.info("------ Fetching watched movies from Plex ------")
    watched_movies = {}
    movies_section = plex.library.section('Movies')
    for movie in movies_section.all():
        if movie.isWatched and movie.lastViewedAt:
            watched_movies[movie.title] = movie.lastViewedAt
    logger.info(f"Found {len(watched_movies)} watched movies.")

    logger.info("------ Unmonitoring watched movies in Radarr ------")
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

    logger.info("------ Collecting movies in Plex collection ------")
    for video in movies_section.search(collection=MOVIE_COLLECTION_NAME):
        MOVIE_COLLECTION.append(video.title)

    logger.info("------ Removing movies not in collection or language filter ------")
    for movie in movies:
        language_info = movie.get("originalLanguage", {})
        language_name = language_info.get("name", "Unknown")
        monitored = movie.get("monitored", True)

        if movie["title"] not in MOVIE_COLLECTION:
            if not monitored:
                if DRY_RUN:
                    logger.debug(f"Dry run: Would remove movie: {movie['title']} - reason: unmonitored")
                else:
                    logger.info(f'Removing movie: {movie["title"]} - reason: unmonitored')
                    delete(f'movie/{movie["id"]}', {'deleteFiles': True, 'addImportExclusion': False})
            elif LANGUAGE_FILTER and language_name not in ACCEPTED_LANGUAGES:
                if DRY_RUN:
                    logger.debug(f"Dry run: Would remove movie: {movie['title']} - language not accepted ({language_name})")
                else:
                    logger.info(f"Removing movie: {movie['title']} - language not accepted")
                    delete(f'movie/{movie['id']}', {'deleteFiles': True, 'addImportExclusion': False})

    logger.info("------ Logging skipped movies ------")
    for movie in MOVIE_COLLECTION:
        logger.info(f"Skipping movie: {movie} - in collection '{MOVIE_COLLECTION_NAME}'")

except Exception as e:
    logger.error(f'An error occurred: {str(e)}')

finally:
    logger.info("====== Script Ended ======")
