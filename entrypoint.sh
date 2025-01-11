#!/bin/bash

# Function to log errors
log_error() {
    echo "ERROR: $1" | tee -a /app/logs/entrypoint.log
}

# Function to log info messages
log_info() {
    echo "INFO: $1" | tee -a /app/logs/entrypoint.log
}

# Function to log warnings
log_warning() {
    echo "WARNING: $1" | tee -a /app/logs/entrypoint.log
}

# Function to check if a value is "true" or "false"
validate_boolean() {
    if [[ "$1" != "true" && "$1" != "false" ]]; then
        log_error "$2 must be either 'true' or 'false', but received: $1. Reverting to default."
        echo "$2=false"  # Default to 'false'
    fi
}

# Initialize an array to hold missing environment variables
missing_vars=()

# Check for required environment variables and optional defaults
check_env_vars() {
    [ -z "$RADARR_URL" ] && missing_vars+=("RADARR_URL")
    [ -z "$RADARR_API_KEY" ] && missing_vars+=("RADARR_API_KEY")
    [ -z "$PLEX_URL" ] && missing_vars+=("PLEX_URL")
    [ -z "$PLEX_TOKEN" ] && missing_vars+=("PLEX_TOKEN")

    # Optional config vars
    if [ -z "$LANGUAGE_FILTER" ]; then
        LANGUAGE_FILTER="false"  # Default to false if not set
    fi
    if [ -z "$DRY_RUN" ]; then
        DRY_RUN="false"  # Default to false if not set
    fi
    if [ -z "$ACCEPTED_LANGUAGES" ]; then
        ACCEPTED_LANGUAGES=""
    fi

    # Do not set defaults here; defer to config.yml if values are missing
    if [ -z "$API_TIMEOUT" ]; then
        API_TIMEOUT=""
    fi
    if [ -z "$STRIKE_COUNT" ]; then
        STRIKE_COUNT=""
    fi
}

# Validate and log errors for booleans and revert to defaults if invalid
validate_booleans() {
    if [[ "$LANGUAGE_FILTER" != "true" && "$LANGUAGE_FILTER" != "false" ]]; then
        log_warning "LANGUAGE_FILTER is invalid: '$LANGUAGE_FILTER'. Reverting to default 'false'."
        LANGUAGE_FILTER="false"
    fi
    if [[ "$DRY_RUN" != "true" && "$DRY_RUN" != "false" ]]; then
        log_warning "DRY_RUN is invalid: '$DRY_RUN'. Reverting to default 'false'."
        DRY_RUN="false"
    fi
}

# Load configuration from config.yml if it exists
load_config_yml() {
    if [ -f /app/config/config.yml ]; then
        log_info "Loading configuration from config.yml"
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ $line =~ ^[^#]*:[^#]*$ ]]; then
                varname=$(echo "$line" | cut -d ':' -f 1 | tr -d '[:space:]')
                varvalue=$(echo "$line" | cut -d ':' -f 2- | tr -d '[:space:]')

                # Validate and handle empty or invalid values
                if [ -z "$varvalue" ]; then
                    log_warning "Value for '$varname' is empty in config.yml. Skipping."
                    continue
                fi

                # Special validation for numeric values (e.g., API_TIMEOUT)
                case "$varname" in
                    api_timeout)
                        if ! [[ "$varvalue" =~ ^[0-9]+$ ]]; then
                            log_warning "Invalid value for '$varname' in config.yml: '$varvalue' is not a number. Skipping."
                            continue
                        fi
                        API_TIMEOUT="$varvalue"
                        log_info "Using API_TIMEOUT from config.yml: $API_TIMEOUT"
                        ;;
                    strike_count)
                        if ! [[ "$varvalue" =~ ^[0-9]+$ ]]; then
                            log_warning "Invalid value for '$varname' in config.yml: '$varvalue' is not a number. Skipping."
                            continue
                        fi
                        STRIKE_COUNT="$varvalue"
                        log_info "Using STRIKE_COUNT from config.yml: $STRIKE_COUNT"
                        ;;
                    *)
                        # If not API_TIMEOUT or STRIKE_COUNT, just set the variable
                        eval "$varname=\"$varvalue\""
                        log_info "Using $varname from config.yml: $varvalue"
                        ;;
                esac
            fi
        done < <(sed 's/\r//g' /app/config/config.yml)
    else
        log_info "config.yml not found. Proceeding with environment variables only."
    fi
}

# Ensure the /app/config directory exists
setup_config_directory() {
    if [ ! -d "/app/config" ]; then
        log_info "/app/config directory not found. Creating it."
        mkdir -p "/app/config"
        chmod -R 777 "/app/config"
    else
        log_info "/app/config directory exists."
    fi
}

# Update config.yml with environment variables
update_config_yml() {
    # Apply defaults if missing and not found in config.yml
    if [ -z "$API_TIMEOUT" ]; then
        API_TIMEOUT="600"
        log_info "Setting default API_TIMEOUT: $API_TIMEOUT"
    fi
    if [ -z "$STRIKE_COUNT" ]; then
        STRIKE_COUNT="5"
        log_info "Setting default STRIKE_COUNT: $STRIKE_COUNT"
    fi

    # Convert booleans to lowercase for YAML format
    LANGUAGE_FILTER=$(echo "$LANGUAGE_FILTER" | tr '[:upper:]' '[:lower:]')
    DRY_RUN=$(echo "$DRY_RUN" | tr '[:upper:]' '[:lower:]')

    # Write to config.yml
    envsubst < /app/config/config.template > /app/config/config.yml
    log_info "Environment variables have been written to config.yml"
}

# Ensure log directory exists and set permissions
setup_log_directory() {
    mkdir -p "/app/logs"
    chmod -R 777 "/app/logs"
}

# Ensure API_TIMEOUT and STRIKE_COUNT are integers
validate_integers() {
    if ! [[ "$API_TIMEOUT" =~ ^[0-9]+$ ]]; then
        log_error "API_TIMEOUT must be an integer, but received: $API_TIMEOUT"
    fi

    if ! [[ "$STRIKE_COUNT" =~ ^[0-9]+$ ]]; then
        log_error "STRIKE_COUNT must be an integer, but received: $STRIKE_COUNT"
    fi
}

# Main script execution
setup_config_directory
check_env_vars

# Validate booleans for LANGUAGE_FILTER and DRY_RUN
validate_booleans

# Load config.yml if it exists
load_config_yml

# Log and exit if any missing required environment variables are found
if [ ${#missing_vars[@]} -ne 0 ]; then
    log_error "The following environment variables are missing: ${missing_vars[*]}"
fi

# Validate that API_TIMEOUT and STRIKE_COUNT are integers
validate_integers

# Write or update config.yml with environment variables
update_config_yml

setup_log_directory

# Execute the main application
exec "$@"