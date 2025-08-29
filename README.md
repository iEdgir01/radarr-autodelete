# Radarr Autodelete

**Radarr Autodelete** is a Python script that helps you manage your Radarr and Plex movie collections by automatically removing unmonitored movies.

## What It Does

- Deletes unmonitored movies from Radarr.
- Can remove movies in unsupported languages:
  - set `LANGUAGE_FILTER` to true if this is required
  - set `ACCEPTED_LANGUAGES` to languages you strictly want i.e. `ACCEPTED_LANGUAGES=English,Japanese,Korean`
- Keeps movies in a specified Plex collection to avoid deletion (defined by `MOVIE_COLLECTION_NAME`).
  - i.e. `MOVIE_COLLECTION_NAME=Keep`
- Unmonitors movies in Radarr if they've been watched in Plex *after* being downloaded.
- Supports Plex user-specific watched history via optional `PLEX_USER_TOKEN`.
- Logs all actions for easy tracking in `/app/logs`.

## Usage

This project has a Dockerfile hosted on Docker Hub for ease of deployment — specifically for OMV setups.

Building Docker images locally on OpenMediaVault can be inconvenient since the OMV environment is web-based. You only need to add the provided `docker-compose.yml` file via the OMV Docker Compose extension or clone the docker-compose file locally and run `docker-compose up`. Check the logs to ensure it's working.

I have created [a dedicated Docker image](https://hub.docker.com/r/iedgir01/radarr_autodelete), which will allow you to use the provided docker-compose file instead of building the image and hosting the codebase locally.

## Testing

Use `DRY_RUN=true` to run the Python script without deleting anything — check the logs for the results. This is to confirm that your language profiles and watched indicators are working as expected.

## `ENVIRONMENT_VARIABLES` Setup:

To configure the script, add these `ENVIRONMENT_VARIABLES` to your Docker Compose.

```bash
# Basic config !!REQUIRED!!
RADARR_URL=http://radarr:port
RADARR_API_KEY=your-radarr-api-key
PLEX_URL=http://plex:port
PLEX_TOKEN=your-plex-token

# Optional: If you want to only target your specific Plex user watch history
# This must be a user authentication token (not the server token)
PLEX_USER_TOKEN=your-user-token

# Language profiles of movies that will be kept
# Enable language filtering to apply this control
LANGUAGE_FILTER=true #true/false — defaults to false
ACCEPTED_LANGUAGES=English,Japanese,Korean #if not set, defaults to an empty list

# Plex collection name — all movies within will be kept
MOVIE_COLLECTION_NAME=plex-collection-name

# Dry Run — for safe testing
DRY_RUN=false #true/false — no actual deletions if true
```