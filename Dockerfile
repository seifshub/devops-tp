FROM python:3.11.12-slim AS base

WORKDIR /app

# Create non-root user FIRST
RUN adduser --disabled-password --gecos '' appuser

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files with correct ownership
COPY --chown=appuser:appuser app/app.py .

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["python", "app.py"]