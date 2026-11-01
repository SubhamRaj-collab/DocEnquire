from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

registry = CollectorRegistry()
http_requests = Counter(
    "rag_http_requests_total",
    "HTTP requests handled by the RAG API",
    ["method", "path", "status"],
    registry=registry,
)
http_errors = Counter(
    "rag_http_errors_total",
    "HTTP requests that completed with an error",
    ["method", "path"],
    registry=registry,
)
request_latency = Histogram(
    "rag_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    registry=registry,
)
time_to_first_token = Histogram(
    "rag_time_to_first_token_seconds",
    "Time from beginning a streamed query to its first generated token",
    registry=registry,
)
ingestion_failures = Counter(
    "rag_ingestion_failures_total",
    "Document ingestion failures",
    registry=registry,
)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST
