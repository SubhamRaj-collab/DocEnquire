from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    chunk_count: int
    collection_name: str
    upload_timestamp: str
    file_size_bytes: int


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    chunk_count: int
    collection_name: str
    upload_timestamp: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_count: int


class DocumentDeleteResponse(BaseModel):
    document_id: str
    filename: str
    chunks_deleted: int
    success: bool
