# Radarr Autodelete

**Radarr Autodelete** is a Python script that helps you manage your Radarr and Plex movie collections by automatically removing unmonitored movies.

## What It Does

- Deletes unmonitored movies from Radarr.
- can remove movies in unsupported languages:
  - set LANGUAGE_FILTER to true if this is required
  - set ACCEPTED_LANGUAGES to languages you strictly want i.e (ACCEPTED_LANGUAGES=English,Japanese,Korean). 
- Keeps movies in a specified Plex collection to avoid deletion (defined by MOVIE_COLLECTION_NAME).
  - i.e (MOVIE_COLLECTION_NAME=Keep)
- Logs all actions for easy tracking in `/app/logs`.

## Usage
This project has a dockerfile hosted on dockerhub for ease of deployment - specifically for OMV setups. 

Building Docker images locally on OpenMediaVault can be inconvenient since the OMV environment is web-based. you only need to add the provided `docker-compose.yml` file via the OMV Docker Compose extension or clone the docker-compose file locally and ``docker-compose up``. Check the logs to ensure it's working.

I have created [a dedicated Docker image](https://hub.docker.com/r/iedgir01/radarr_autodelete), which will allow you to use the provided docker-compose file instead of building the image and hosting the codebase locally.

## Testing
Use `DRY_RUN=true` to run the python script without deleting anything - check the logs for the results. This is to confirm that your langugae profiles and watched indicators are working as expected.

## `ENVIRONMENT_VARIABLES` Setup - this creates the config.yml values within /config from config.template.

To configure the script add these ENVIROMENT_VARIABLES to the docker compose or edit the `config.template` file and save it as `config.yml`.
the config.yml needs to be saved inside ``/path/to/your/radarr_autodelete/config``.

```bash
#basic config !!REQUIRED!!
RADARR_URL=http://radarr:port
RADARR_API_KEY=your-radarr-api-key
PLEX_URL=http://plex:port
PLEX_TOKEN=your-plex-token

#enable language filtering for accepted languages
LANGUAGE_FILTER=true #true/false
#language profiles of movies that will be kept - all else will be removed
ACCEPTED_LANGUAGES=English,Japanese,Korean

#plex collection name of which all movies within, will be kept
MOVIE_COLLECTION_NAME=plex collection name

#Dry Run - Testing
DRY_RUN=false #true/false
```
