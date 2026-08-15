from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    vector_store: str = "chromadb"
    document_count: int
    collection_count: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
