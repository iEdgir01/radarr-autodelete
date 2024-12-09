# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a logs directory within the container
RUN mkdir -p logs

# Make the logs directory writable
RUN chmod -R 777 logs

# Copy the rest of the application code to the working directory
COPY . .

# Ensure the config.yml file is copied
COPY config.yml /app/config.yml

# Default command to run when no command is specified
ENTRYPOINT ["python", "radarr-autodelete.py"]