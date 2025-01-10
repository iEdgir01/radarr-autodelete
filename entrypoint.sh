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
    DRY_RUN=${DRY_RUN:-false}
    MOVIE_COLLECTION_NAME=${MOVIE_COLLECTION_NAME:-}
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
    mkdir -p "/app/logs"
    chmod -R 777 "/app/logs"
}

# Main script execution
check_env_vars

# Write or update config.yml with environment variables
update_config_yml

if [ -f /app/config/config.yml ]; then
    log_info "Loading configuration from config.yml"
    # Load the config file as environment variables
    # Use sed to replace carriage returns and remove double quotes
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ $line =~ ^[^#]*:[^#]*$ ]]; then
            varname=$(echo "$line" | cut -d ':' -f 1 | tr -d '[:space:]')
            varvalue=$(echo "$line" | cut -d ':' -f 2- | tr -d '[:space:]')
            eval "$varname=\"$varvalue\""
        fi
    done < <(sed 's/\r//g' /app/config/config.yml)
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