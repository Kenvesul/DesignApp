# DesignApp v2.0 — Production Docker image
# Python 3.12 + Gunicorn

FROM python:3.12-slim

LABEL maintainer="DesignApp"
LABEL description="Eurocode 7 Geotechnical Analysis Suite"

# System deps for matplotlib (fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Expose internal port
EXPOSE 5000

# Gunicorn entry point
# Workers: 2 × CPU + 1 is a common heuristic; override via WORKERS env var
CMD gunicorn \
    --workers  "${WORKERS:-4}" \
    --threads  2 \
    --bind     "0.0.0.0:${PORT:-5000}" \
    --timeout  120 \
    --access-logfile - \
    --error-logfile  - \
    "ui.app:app"
