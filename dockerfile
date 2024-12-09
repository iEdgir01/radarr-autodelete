FROM python:3.9-slim-buster
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p logs
RUN chmod -R 777 logs
RUN mkdir -p config
RUN chmod -R 777 config
COPY config.yml ./config
COPY . .
ENTRYPOINT ["python", "radarr-autodelete.py"]