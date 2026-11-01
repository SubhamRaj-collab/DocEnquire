import logging
import re
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.core.metrics import http_errors, http_requests, request_latency
from src.core.request_context import request_id_var

logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        supplied_id = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = (
            supplied_id if REQUEST_ID_PATTERN.fullmatch(supplied_id) else str(uuid4())
        )
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        route = "__unmatched__"

        async def send_with_observability(message: Message) -> None:
            nonlocal status_code, route
            if message["type"] == "http.response.start":
                status_code = message["status"]
                matched_route = scope.get("route")
                route = getattr(matched_route, "path", None) or "__unmatched__"
                response_headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            elif message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                elapsed = time.perf_counter() - started
                http_requests.labels(scope["method"], route, str(status_code)).inc()
                request_latency.labels(scope["method"], route).observe(elapsed)
                if status_code >= 400:
                    http_errors.labels(scope["method"], route).inc()
            await send(message)

        try:
            await self.app(scope, receive, send_with_observability)
        except Exception:
            if status_code == 500:
                http_requests.labels(scope["method"], route, "500").inc()
                http_errors.labels(scope["method"], route).inc()
                request_latency.labels(scope["method"], route).observe(
                    time.perf_counter() - started
                )
            logger.exception("Unhandled request error")
            raise
        finally:
            request_id_var.reset(token)
