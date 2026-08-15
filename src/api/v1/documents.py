import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.core.config import Settings
from src.core.exceptions import FileTooLargeError, IngestionError, UnsupportedFormatError
from src.dependencies import get_file_store, get_ingestion_pipeline, get_settings, get_vector_store
from src.ingestion.pipeline import IngestionPipeline
from src.schemas.documents import (
    DocumentDeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
)
from src.storage.file_store import FileStore
from src.vectorstore.chroma_store import ChromaStore

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".md", ".markdown", ".txt"}


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = Form(default="default"),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    settings: Settings = Depends(get_settings),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file format '{ext}'. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        if len(content) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
            )
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await pipeline.ingest(
            file_path=tmp_path,
            filename=file.filename,
            collection_name=collection_name,
        )
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except IngestionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return DocumentUploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        doc_type=result.doc_type,
        chunk_count=result.chunk_count,
        collection_name=result.collection_name,
        upload_timestamp=result.upload_timestamp,
        file_size_bytes=result.file_size_bytes,
    )


@router.post("/upload/batch", response_model=list[DocumentUploadResponse], status_code=201)
async def upload_documents_batch(
    files: list[UploadFile] = File(...),
    collection_name: str = Form(default="default"),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    settings: Settings = Depends(get_settings),
):
    results = []
    for file in files:
        if not file.filename:
            continue
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            if len(content) > settings.max_upload_size_mb * 1024 * 1024:
                continue
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = await pipeline.ingest(
                file_path=tmp_path,
                filename=file.filename,
                collection_name=collection_name,
            )
            results.append(
                DocumentUploadResponse(
                    document_id=result.document_id,
                    filename=result.filename,
                    doc_type=result.doc_type,
                    chunk_count=result.chunk_count,
                    collection_name=result.collection_name,
                    upload_timestamp=result.upload_timestamp,
                    file_size_bytes=result.file_size_bytes,
                )
            )
        except Exception:
            pass
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return results


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    collection_name: str = "default",
    store: ChromaStore = Depends(get_vector_store),
):
    docs = store.list_documents(collection_name=collection_name)
    return DocumentListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total_count=len(docs),
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    collection_name: str = "default",
    store: ChromaStore = Depends(get_vector_store),
    file_store: FileStore = Depends(get_file_store),
):
    docs = store.list_documents(collection_name=collection_name)
    doc_info = next((d for d in docs if d["document_id"] == document_id), None)
    if not doc_info:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    chunks_deleted = store.delete_by_document_id(document_id, collection_name=collection_name)
    file_store.delete(document_id)

    return DocumentDeleteResponse(
        document_id=document_id,
        filename=doc_info.get("filename", ""),
        chunks_deleted=chunks_deleted,
        success=True,
    )
