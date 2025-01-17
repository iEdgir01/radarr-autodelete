FROM python:3.9-slim-buster

# Install gettext package for envsubst
RUN apt-get update && apt-get install -y gettext && apt-get clean

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create and set permissions for logs directory
RUN mkdir -p logs
RUN chmod -R 777 logs

# Copy all application files into the working directory
COPY . .

# Default command to run the application
CMD ["python", "radarr-autodelete.py"]