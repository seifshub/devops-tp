FROM python:3.11-slim AS base

# Set working directory inside container
WORKDIR /app

# Copy dependencies file first (Docker caching optimization)
# If requirements.txt didn't change, Docker reuses the cached layer
COPY app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ .

# Create a non-root user for security 
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Tell Docker this container listens on port 5000
EXPOSE 5000

# Health check: Docker will verify the app is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Start the app
CMD ["python", "app.py"]
