import yaml
import logging
import os
import requests
from datetime import datetime
from plexapi.myplex import PlexServer
from plexapi.exceptions import PlexApiException
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Load configuration from config.yml
config_file = os.path.join(os.path.dirname(__file__), 'config', 'config.yml')
with open(config_file, 'r') as file:
    config = yaml.safe_load(file)

# Extract configuration values
RADARR_URL = config['radarr']['url']
RADARR_API_KEY = config['radarr']['api_key']
PLEX_URL = config['plex']['url']
PLEX_TOKEN = config['plex']['token']
ACCEPTED_LANGUAGES = config['accepted_languages']
COLLECTION_NAME = config['movie_collection_name']
LOG_DIR = config['log_directory']

# Create the logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
log_file = os.path.join(LOG_DIR, 'radarr-autodelete.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(levelname)s[%(name)s]:%(message)s')

# Log script start
logging.info('Script started.')

# Configure Radarr API connection
API_EXTENSION = '/api/v3/'
API_HOST = urljoin(RADARR_URL, API_EXTENSION)
logging.info(f'API URL: {API_HOST}')

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
    # Ensure service is reachable with retry
    logging.info('Checking Plex service reachability...')
    plex = connect_to_plex(PLEX_URL, PLEX_TOKEN)
    logging.info('Plex service is reachable. Proceeding with script execution.')

    logging.info('Checking Radarr service reachability...')
    movies = get('movie', {})
    logging.info('Radarr service is reachable. Proceeding with script execution.')

    # Get the list of movies from Plex that should not be deleted
    movies_section = plex.library.section('Movies')
    for video in movies_section.search(collection=COLLECTION_NAME):
        MOVIE.append(video.title)

    # Get movies from Radarr and process them
    for movie in movies:
        language = movie.get("originalLanguage", {}).get("name", "Unknown")
        monitored = movie.get("monitored", True)
        
        if movie["title"] not in MOVIE:
            if not monitored:
                logging.info(f'removing movie : {movie["title"]} - reason : unmonitored')
                logging.info('--------------------------------------------------')
                deletefiles = True
                addImportExclusion = False
                delete(f'movie/{movie["id"]}', {'deleteFiles': deletefiles, 'addImportExclusion': addImportExclusion})
            elif language not in ACCEPTED_LANGUAGES:
                logging.info(f'removing movie : {movie["title"]} - reason : Incorrect language profile')
                logging.info('--------------------------------------------------')
                deletefiles = True
                addImportExclusion = False
                delete(f'movie/{movie["id"]}', {'deleteFiles': deletefiles, 'addImportExclusion': addImportExclusion})
            else:
                continue
    
    for movie in MOVIE:
        logging.info(f"skipping movie : {movie} - reason : in collection {COLLECTION_NAME}")
        logging.info('--------------------------------------------------')
        
except Exception as e:
    # Log any exceptions that occur
    logging.error(f'An error occurred: {str(e)}')

finally:
    # Log script end
    logging.info('Script ended.')