from fastapi import Request

from src.core.config import Settings
from src.ingestion.pipeline import IngestionPipeline
from src.llm.base import LLMProvider
from src.rag.pipeline import RAGPipeline
from src.storage.file_store import FileStore
from src.vectorstore.chroma_store import ChromaStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_vector_store(request: Request) -> ChromaStore:
    return request.app.state.vector_store


def get_ingestion_pipeline(request: Request) -> IngestionPipeline:
    return request.app.state.ingestion_pipeline


def get_rag_pipeline(request: Request) -> RAGPipeline:
    return request.app.state.rag_pipeline


def get_llm(request: Request) -> LLMProvider:
    return request.app.state.llm


def get_file_store(request: Request) -> FileStore:
    return request.app.state.file_store
