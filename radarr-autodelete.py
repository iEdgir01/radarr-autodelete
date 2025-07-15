import logging
import os
import sys
import requests
from datetime import datetime
from plexapi.myplex import PlexServer
from plexapi.exceptions import PlexApiException
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        logger.error(f"Invalid value for {var} boolean conversion: {value}. Expected 'true' or 'false'.")
        raise ValueError(f"Invalid value for {var}: {value}. Expected 'true' or 'false'.")

RADARR_URL = os.getenv('RADARR_URL')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')
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
        logger.debug(f'Detailed delete parameters: {extra_params}')
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
    logger.info('Plex service is reachable. Proceeding with script execution.')

    logger.info('Checking Radarr service reachability...')
    movies = get('movie', {})
    logger.info('Radarr service is reachable. Proceeding with script execution.')
    
    watched_movies = {}
    logger.info("Checking Plex for watched movies...")
    try:
        movies_section = plex.library.section('Movies')
        for video in movies_section.all():
            if video.isWatched and video.lastViewedAt:
                watched_movies[video.title] = video.lastViewedAt
        logger.info(f"Found {len(watched_movies)} watched movies with view dates in Plex.")
    except Exception as e:
        logger.error(f"Error fetching watched movies from Plex: {str(e)}")

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
                        logger.debug(f"Dry run: Would unmonitor movie in Radarr: {title} — watched after it was added "
                                    f"(last viewed: {viewed_dt}, added: {added_dt})")
                        logger.debug('--------------------------------------------------')
                    else:
                        movie['monitored'] = False
                        update_url = f'movie/{movie["id"]}'
                        response = requests.put(
                            urljoin(API_HOST, update_url),
                            params={'apikey': RADARR_API_KEY},
                            json=movie
                        )
                        response.raise_for_status()
                        logger.info(f"Unmonitored movie in Radarr: {title} — watched after it was added")
                        logger.info('--------------------------------------------------')
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
                    logger.debug('--------------------------------------------------')
                else:
                    logger.info(f'Removing movie: {movie["title"]} - reason: unmonitored')
                    logger.info('--------------------------------------------------')
                    deletefiles = True
                    addImportExclusion = False
                    delete(f'movie/{movie["id"]}', {'deleteFiles': deletefiles, 'addImportExclusion': addImportExclusion})
            else:
                if LANGUAGE_FILTER:
                    if language not in ACCEPTED_LANGUAGES:
                        if DRY_RUN:
                            logger.debug(f"Dry run: Would remove movie: {movie['title']} - reason: Incorrect language profile ({language})\n"
                                        f" language filter: {LANGUAGE_FILTER}\n"
                                        f" accepted_languages ({ACCEPTED_LANGUAGES})")
                            logger.debug('--------------------------------------------------')
                        else: 
                            logger.info(f'Removing movie: {movie["title"]} - reason: Incorrect language profile')
                            logger.info('--------------------------------------------------')
                            deletefiles = True
                            addImportExclusion = False
                            delete(f'movie/{movie["id"]}', {'deleteFiles': deletefiles, 'addImportExclusion': addImportExclusion})

    for movie in MOVIE:
        logger.info(f"Skipping movie: {movie} - reason: in collection {COLLECTION_NAME}")
        logger.info('--------------------------------------------------')

except Exception as e:
    logger.error(f'An error occurred: {str(e)}')

finally:
    logger.info('Script ended.')