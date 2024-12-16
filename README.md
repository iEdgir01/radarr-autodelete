# Radarr Autodelete

**Radarr Autodelete** is a Python script that helps you manage your Radarr and Plex movie collections by automatically removing unmonitored movies.

## What It Does

- Deletes unmonitored movies from Radarr.
- Removes movies in unsupported languages (defined by accepted_languages in the config.yml). 
- Keeps movies in a specified Plex collection to avoid deletion (defined by movie collection name in the config.yml).
- Logs all actions for easy tracking.

This project has a dockerfile hosted on dockerhub for ease of deployment - specifically for OMV setups. 
Building Docker images locally on OpenMediaVault can be inconvenient since the OMV environment is web-based. you only need to add the provided `docker-compose.yml` file via the OMV Docker Compose extension or clone the docker-compose fil locally and ``docker-compose up``. Check the logs to ensure it's working.

I have created [a dedicated Docker image](https://hub.docker.com/r/iedgir01/radarr_autodelete), which will allow you to use the provided docker-compose file instead of building the image and hosting the codebase locally.