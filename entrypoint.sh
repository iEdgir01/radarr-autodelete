#!/bin/bash

# Logging functions
log_error() {
    echo "ERROR: $1" | tee -a /app/logs/entrypoint.log
}

log_info() {
    echo "INFO: $1" | tee -a /app/logs/entrypoint.log
}

log_warning() {
    echo "WARNING: $1" | tee -a /app/logs/entrypoint.log
}

# Validate boolean values
validate_boolean() {
    if [[ "$1" != "true" && "$1" != "false" ]]; then
        log_error "$2 must be either 'true' or 'false', but received: $1. Reverting to default."
        echo "$2=false"  # Default to 'false'
    fi
}

# Initialize an array to hold missing environment variables
missing_vars=()

# Check for required environment variables and set optional defaults
check_env_vars() {
    [ -z "$RADARR_URL" ] && missing_vars+=("RADARR_URL")
    [ -z "$RADARR_API_KEY" ] && missing_vars+=("RADARR_API_KEY")
    [ -z "$PLEX_URL" ] && missing_vars+=("PLEX_URL")
    [ -z "$PLEX_TOKEN" ] && missing_vars+=("PLEX_TOKEN")

    # Optional config vars with defaults
    : "${LANGUAGE_FILTER:=false}"
    : "${DRY_RUN:=false}"
    : "${ACCEPTED_LANGUAGES:=}"
}

# Validate boolean environment variables
validate_booleans() {
    validate_boolean "$LANGUAGE_FILTER" "LANGUAGE_FILTER"
    validate_boolean "$DRY_RUN" "DRY_RUN"
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

# Load configuration from config.yml if it exists
load_config_yml() {
    if [ -f /app/config/config.yml ]; then
        log_info "Loading configuration from config.yml"
        current_section=""
        buffer=""

        while IFS= read -r line || [ -n "$line" ]; do
            line="${line#"${line%%[![:space:]]*}"}"  # Remove leading whitespace
            line="${line%"${line##*[![:space:]]}"}"  # Remove trailing whitespace

            # Skip empty lines and comments
            if [[ -z "$line" || "$line" =~ ^# ]]; then
                continue
            fi

            # Check for section headers
            if [[ $line =~ ^[^:]+:[[:space:]]*$ ]]; then
                buffer="$line"
                continue
            fi

            if [[ -n "$buffer" && $line =~ ^[[:space:]]+[^:]+:[[:space:]]* ]]; then
                current_section="${buffer%%:*}"
                current_section="${current_section//[:space:]/}"
                buffer=""
                continue
            fi

            if [[ -n "$buffer" ]]; then
                buffer=""
                current_section=""
            fi

            if [[ ! "$line" =~ ^[[:space:]]+ ]]; then
                current_section=""
            fi

            # Handle key-value pairs
            if [[ $line =~ ^[^:]+:[^:]*$ ]]; then
                varname="${line%%:*}"
                varvalue="${line#*:}"
                varname="${varname//[:space:]/}"
                varvalue="${varvalue//[:space:]/}"

                if [ -n "$current_section" ]; then
                    varname="${current_section}_${varname}"
                fi

                # Prioritize environment variable value over config file value
                env_value=$(printenv "$varname")
                if [ -n "$env_value" ]; then
                    varvalue="$env_value"
                fi

                if [ -z "$varvalue" ]; then
                    log_warning "Value for '$varname' is empty in config.yml and no environment variable found. Skipping."
                    continue
                fi

                eval "$varname=\"$varvalue\""
                log_info "Using $varname: $varvalue"
            fi
        done < /app/config/config.yml
    else
        log_info "config.yml not found. Proceeding with environment variables only."
    fi
}

# Update config.yml with environment variables
update_config_yml() {
    LANGUAGE_FILTER="${LANGUAGE_FILTER,,}"
    DRY_RUN="${DRY_RUN,,}"

    envsubst < /app/config/config.template > /app/config/config.yml
    log_info "Environment variables have been written to config.yml"
}

# Ensure log directory exists and set permissions
setup_log_directory() {
    mkdir -p "/app/logs"
    chmod -R 777 "/app/logs"
}

# Check for missing values (prioritize environment variables over config.yml)
check_missing_values() {
    for var in "${missing_vars[@]}"; do
        env_value=$(printenv "$var")
        if [ -z "$env_value" ] && [ -z "$(eval echo \$$var)" ]; then
            log_error "$var is required but not set in the environment or config.yml. Exiting."
            exit 1
        fi
    done
}

# Main script execution
setup_config_directory
check_env_vars
validate_booleans
load_config_yml
# Log and continue if any missing required environment variables are found
if [ ${#missing_vars[@]} -ne 0 ]; then
    log_warning "The following environment variables are missing: ${missing_vars[*]}"
fi
check_missing_values
update_config_yml
setup_log_directory

exec "$@"