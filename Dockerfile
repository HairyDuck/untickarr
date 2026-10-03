# Untickarr - Transmission file filter for Sonarr/Radarr tagged torrents
# Runs on Synology NAS Container Manager
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/

# Persistent data (config, DB) - mount at /data
ENV DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 4444

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4444/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4444"]
