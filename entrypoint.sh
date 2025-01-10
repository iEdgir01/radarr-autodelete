#!/bin/bash

# Replace placeholders in config.template and output to config.yml
envsubst < /app/config/config.template > /app/config/config.yml

# Execute the main application
exec "$@"