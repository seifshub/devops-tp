from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

app = Flask(__name__)

# Prometheus metrics — these let Prometheus scrape our app
REQUEST_COUNT = Counter(
    'flask_request_count',
    'Total request count',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'flask_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)

@app.route('/')
def home():
    start = time.time()
    REQUEST_COUNT.labels('GET', '/', 200).inc()
    REQUEST_LATENCY.labels('/').observe(time.time() - start)
    return jsonify({
        "message": "Hello from Flask DevOps App!",
        "status": "healthy",
        "version": "1.0"
    })

@app.route('/health')
def health():
    # Jenkins smoke test will call this endpoint
    return jsonify({"status": "UP"}), 200

@app.route('/metrics')
def metrics():
    # Prometheus will scrape this endpoint
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
