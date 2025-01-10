# Radarr Autodelete

**Radarr Autodelete** is a Python script that helps you manage your Radarr and Plex movie collections by automatically removing unmonitored movies.

## What It Does

- Deletes unmonitored movies from Radarr.
- can remove movies in unsupported languages:
  - set LANGUAGE_FILTER to true if this is required
  - set ACCEPTED_LANGUAGES to languages you strictly want i.e (ACCEPTED_LANGUAGES=English,Japanese,Korean). 
- Keeps movies in a specified Plex collection to avoid deletion (defined by MOVIE_COLLECTION_NAME).
- Logs all actions for easy tracking.

## Usage
This project has a dockerfile hosted on dockerhub for ease of deployment - specifically for OMV setups. 

Building Docker images locally on OpenMediaVault can be inconvenient since the OMV environment is web-based. you only need to add the provided `docker-compose.yml` file via the OMV Docker Compose extension or clone the docker-compose file locally and ``docker-compose up``. Check the logs to ensure it's working.

I have created [a dedicated Docker image](https://hub.docker.com/r/iedgir01/radarr_autodelete), which will allow you to use the provided docker-compose file instead of building the image and hosting the codebase locally.

## `ENVIRONMENT_VARIABLES` Setup - this modifies the config.yml values within /config.

To configure the script add these ENVIROMENT_VARIABLES to the docker compose / OMV setup or edit the `config.yml` file with your radarr and plex url and api key / token.
the config.yml needs to be saved inside ``/path/to/your/radarr_autodelete/config``.

```bash
#basic config !!REQUIRED!!
RADARR_URL=http://radarr:port
RADARR_API_KEY=your-radarr-api-key
PLEX_URL=http://plex:port
PLEX_TOKEN=your-plex-token

#enable language filtering for accepted languages
LANGUAGE_FILTER=true
#language profiles of movies that will be kept - all else will be removed
ACCEPTED_LANGUAGES=English,Japanese,Korean

#plex collection name of which all movies within, will be kept
MOVIE_COLLECTION_NAME=plex collection name

#logging
LOG_DIRECTORY=/app/logs
```