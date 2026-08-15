from fastapi import APIRouter, Depends

from src.core.config import Settings
from src.dependencies import get_settings, get_vector_store
from src.schemas.common import HealthResponse
from src.vectorstore.chroma_store import ChromaStore

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    store: ChromaStore = Depends(get_vector_store),
):
    collections = store.list_collections()
    doc_count = 0
    for coll_name in collections:
        doc_count += store.collection_count(coll_name)

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        llm_model=settings.ollama_llm_model,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.ollama_embedding_model,
        document_count=doc_count,
        collection_count=len(collections),
    )
