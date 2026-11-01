# Northstar Local Deployment Checklist

## Startup
Start PostgreSQL, Chroma, and Ollama before checking the API health endpoint. Confirm the configured language and embedding models are present in Ollama.

## Smoke checks
The API listens on port 8000. Prometheus listens on port 9090. Grafana listens on port 3000. The API metrics path is `/metrics`.

## Observability
Check request totals, HTTP errors, request latency, time to first generated token, and ingestion failures. Send a sample query before expecting the dashboard to show non-zero traffic.

## Recovery
Keep persistent volumes for PostgreSQL, Chroma, uploads, and Ollama model weights. Back up volumes before changing service versions.

## Security
The sample Compose credentials are for local development only. Replace them before shared use. The internal-only network overlay blocks external container egress but still permits communication among its attached services.
