FROM python:3.11-slim

WORKDIR /app

# Install production dependencies only (slim subset of requirements.txt)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application source
COPY . .

# Create data directory for SQLite DB (will be overridden by PVC mount)
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gthread", "--threads", "4", "--workers", "1", "--keep-alive", "30", "--timeout", "360", "app:app"]
