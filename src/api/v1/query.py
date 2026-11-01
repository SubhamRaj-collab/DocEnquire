import logging

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.dependencies import get_rag_pipeline
from src.rag.pipeline import RAGPipeline
from src.schemas.query import QueryRequest, QueryResponse
from src.core.metrics import http_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    rag: RAGPipeline = Depends(get_rag_pipeline),
):
    result = await rag.query(
        question=request.question,
        collection_name=request.collection_name,
        top_k=request.top_k,
        temperature=request.temperature,
        metadata_filter=request.metadata_filter,
    )
    return QueryResponse(**result)


@router.post("/stream")
async def query_documents_stream(
    request: QueryRequest,
    rag: RAGPipeline = Depends(get_rag_pipeline),
):
    async def event_generator():
        try:
            async for event in rag.query_stream(
                question=request.question,
                collection_name=request.collection_name,
                top_k=request.top_k,
                temperature=request.temperature,
            ):
                yield {"data": event}
        except Exception:
            http_errors.labels("POST", "/api/v1/query/stream").inc()
            logger.exception("Streaming query failed")
            yield {"event": "error", "data": "The query could not be completed"}

    return EventSourceResponse(event_generator())
