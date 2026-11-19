
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Apply available Debian security updates
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ .

# Create a non-root user and database directory
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 5000

# Initialize database once, then start Gunicorn
CMD ["sh", "-c", "python init_db.py && exec gunicorn --bind 0.0.0.0:5000 --workers 2 app:app"]
