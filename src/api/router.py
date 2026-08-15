from fastapi import APIRouter

from src.api.v1 import collections, documents, health, query

api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1/health", tags=["health"])
api_router.include_router(documents.router, prefix="/v1/documents", tags=["documents"])
api_router.include_router(query.router, prefix="/v1/query", tags=["query"])
api_router.include_router(collections.router, prefix="/v1/collections", tags=["collections"])
