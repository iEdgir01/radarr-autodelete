#!/bin/bash

# Function to log errors and exit
log_error_and_exit() {
    echo "ERROR: $1" | tee -a /app/logs/entrypoint.log
    exit 1
}

# Function to log info messages
log_info() {
    echo "INFO: $1" | tee -a /app/logs/entrypoint.log
}

# Initialize an array to hold missing environment variables
missing_vars=()

# Check for required environment variables and set defaults for non-critical ones
check_env_vars() {
    [ -z "$RADARR_URL" ] && missing_vars+=("RADARR_URL")
    [ -z "$RADARR_API_KEY" ] && missing_vars+=("RADARR_API_KEY")
    [ -z "$PLEX_URL" ] && missing_vars+=("PLEX_URL")
    [ -z "$PLEX_TOKEN" ] && missing_vars+=("PLEX_TOKEN")
    LANGUAGE_FILTER=${LANGUAGE_FILTER:-false}
    if [ "$LANGUAGE_FILTER" = true ] && [ -z "$ACCEPTED_LANGUAGES" ]; then
        missing_vars+=("ACCEPTED_LANGUAGES (required if LANGUAGE_FILTER is true)")
    fi
    MOVIE_COLLECTION_NAME=${MOVIE_COLLECTION_NAME:-}
    LOG_DIRECTORY=${LOG_DIRECTORY:-/app/logs}
}

# Check for required config variables
check_config_vars() {
    [ -z "$RADARR_URL" ] && missing_vars+=("RADARR_URL")
    [ -z "$RADARR_API_KEY" ] && missing_vars+=("RADARR_API_KEY")
    [ -z "$PLEX_URL" ] && missing_vars+=("PLEX_URL")
    [ -z "$PLEX_TOKEN" ] && missing_vars+=("PLEX_TOKEN")
    if [ "$LANGUAGE_FILTER" = true ] && [ -z "$ACCEPTED_LANGUAGES" ]; then
        missing_vars+=("ACCEPTED_LANGUAGES (required if LANGUAGE_FILTER is true)")
    fi
}

# Update config.yml with environment variables
update_config_yml() {
    envsubst < /app/config/config.template > /app/config/config.yml
    log_info "Environment variables have been written to config.yml"
}

# Ensure log directory exists and set permissions
setup_log_directory() {
    mkdir -p "$LOG_DIRECTORY"
    chmod -R 777 "$LOG_DIRECTORY"
}

# Main script execution
check_env_vars

# Write or update config.yml with environment variables
update_config_yml

if [ -f /app/config/config.yml ]; then
    log_info "Loading configuration from config.yml"
    config_vars=$(grep -v '^#' /app/config/config.yml | sed 's/: /=/' | xargs)
    eval $config_vars
    check_config_vars
else
    log_info "config.yml not found."
fi

# Log and exit if any missing environment variables are found
if [ ${#missing_vars[@]} -ne 0 ]; then
    log_error_and_exit "The following environment variables are missing: ${missing_vars[*]}"
fi

setup_log_directory

# Execute the main application
exec "$@"