FROM python:3.9-slim-buster

# Install gettext package for envsubst
RUN apt-get update && apt-get install -y gettext && apt-get clean

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create and set permissions for logs and config directories
RUN mkdir -p logs config
RUN chmod -R 777 logs config

# Copy the config template and application files
COPY config.template ./config/config.template
COPY . .

# Add the entrypoint script for substitution
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command to run the application
CMD ["python", "radarr-autodelete.py"]