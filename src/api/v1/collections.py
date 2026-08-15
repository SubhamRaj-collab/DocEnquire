from fastapi import APIRouter, Depends

from src.dependencies import get_vector_store
from src.vectorstore.chroma_store import ChromaStore

router = APIRouter()


@router.get("/")
async def list_collections(
    store: ChromaStore = Depends(get_vector_store),
):
    names = store.list_collections()
    return {
        "collections": [
            {"name": name, "document_count": store.collection_count(name)}
            for name in names
        ]
    }
