from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings, load_prompt
from src.core.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    LLMProviderError,
    UnsupportedFormatError,
)
from src.core.logging import setup_logging
from src.ingestion.parsers.registry import ParserRegistry
from src.ingestion.pipeline import IngestionPipeline
from src.llm.factory import ProviderFactory
from src.rag.citation_parser import CitationParser
from src.rag.context_builder import ContextBuilder
from src.rag.pipeline import RAGPipeline
from src.rag.retriever import ChromaRetriever
from src.storage.file_store import FileStore
from src.vectorstore.chroma_store import ChromaStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    settings = get_settings()
    app.state.settings = settings

    app.state.llm = ProviderFactory.create_llm(settings)
    embedder = ProviderFactory.create_embedder(settings)
    app.state.embedder = embedder

    app.state.vector_store = ChromaStore(
        persist_directory=settings.chroma_persist_dir,
        embedding_function=embedder.langchain_embeddings,
    )

    parser_registry = ParserRegistry()
    parser_registry.register_defaults()

    app.state.file_store = FileStore(base_dir=settings.upload_dir)

    app.state.ingestion_pipeline = IngestionPipeline(
        parser_registry=parser_registry,
        vector_store=app.state.vector_store,
        file_store=app.state.file_store,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    retriever = ChromaRetriever(app.state.vector_store)
    system_prompt = load_prompt("rag_system.txt")

    app.state.rag_pipeline = RAGPipeline(
        retriever=retriever,
        context_builder=ContextBuilder(),
        llm_provider=app.state.llm,
        citation_parser=CitationParser(),
        system_prompt=system_prompt,
    )

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise Document Q&A",
        description="RAG-powered document question answering with source attribution",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(UnsupportedFormatError)
    async def unsupported_format_handler(request, exc):
        return JSONResponse(status_code=415, content={"error": str(exc)})

    @app.exception_handler(DocumentNotFoundError)
    async def doc_not_found_handler(request, exc):
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(LLMProviderError)
    async def llm_error_handler(request, exc):
        return JSONResponse(status_code=502, content={"error": "LLM provider error", "detail": str(exc)})

    @app.exception_handler(FileTooLargeError)
    async def file_too_large_handler(request, exc):
        return JSONResponse(status_code=413, content={"error": str(exc)})

    from src.api.router import api_router

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
