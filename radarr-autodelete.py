import logging
import os
import sys
import requests
from datetime import datetime
from plexapi.myplex import PlexServer
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
sys.stdout.flush()  # Ensure stdout is flushed immediately
logger.addHandler(stream_handler)

# Convert environment variable to boolean
def str_to_bool(var, value):
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    else:
        logger.error(f"Invalid value for {var} boolean conversion: {value}. Expected 'true' or 'false'.")
        raise ValueError(f"Invalid value for {var}: {value}. Expected 'true' or 'false'.")

# Extract configuration values from environment variables without defaults
RADARR_URL = os.getenv('RADARR_URL')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')
ACCEPTED_LANGUAGES = os.getenv('ACCEPTED_LANGUAGES', '').split(',')
COLLECTION_NAME = os.getenv('MOVIE_COLLECTION_NAME')

# Get environment variable values and set to True/False
try:
    LANGUAGE_FILTER = str_to_bool('LANGUAGE_FILTER', os.getenv('LANGUAGE_FILTER', 'false'))  # Default to 'false' if not set
    DRY_RUN = str_to_bool('DRY_RUN', os.getenv('DRY_RUN', 'false'))  # Default to 'false' if not set
    # Log DRY_RUN values right after processing the environment variables
    if DRY_RUN:
        logger.setLevel(logging.DEBUG)
except ValueError as e:
    logger.error(str(e))

# Log script start and environment variables
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

# Configure Radarr API connection
API_EXTENSION = '/api/v3/'
API_HOST = urljoin(RADARR_URL, API_EXTENSION)
logger.info(f'API URL: {API_HOST}')

MOVIE = []

# Retry mechanism for making requests
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

# Main script logic
try:
    # Ensure Plex service is reachable
    logger.info('Checking Plex service reachability...')
    plex = connect_to_plex(PLEX_URL, PLEX_TOKEN)
    logger.info('Plex service is reachable. Proceeding with script execution.')

    # Ensure Radarr service is reachable
    logger.info('Checking Radarr service reachability...')
    movies = get('movie', {})
    logger.info('Radarr service is reachable. Proceeding with script execution.')

    # Get the list of movies from Plex that should not be deleted
    movies_section = plex.library.section('Movies')
    for video in movies_section.search(collection=COLLECTION_NAME):
        MOVIE.append(video.title)

    # Process movies in Radarr
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

    # Log movies that are skipped
    for movie in MOVIE:
        logger.info(f"Skipping movie: {movie} - reason: in collection {COLLECTION_NAME}")
        logger.info('--------------------------------------------------')

except Exception as e:
    # Log any exceptions that occur
    logger.error(f'An error occurred: {str(e)}')

finally:
    # Log script end
    logger.info('Script ended.')