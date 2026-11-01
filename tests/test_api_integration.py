from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from src.main import create_app


def test_metrics_endpoint_and_api_validation() -> None:
    app = create_app()

    @asynccontextmanager
    async def no_startup(_app):
        yield

    app.router.lifespan_context = no_startup
    app.state.rag_pipeline = object()

    with TestClient(app) as client:
        metrics = client.get("/metrics", headers={"X-Request-ID": "test-request"})
        invalid_query = client.post(
            "/api/v1/query/",
            json={"question": "", "top_k": 5},
        )

    assert metrics.status_code == 200
    assert metrics.headers["x-request-id"] == "test-request"
    assert b"rag_http_requests_total" in metrics.content
    assert invalid_query.status_code == 422
