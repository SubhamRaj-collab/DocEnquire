from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    collection_name: str = Field(default="default")
    top_k: int = Field(default=5, ge=1, le=20)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    metadata_filter: dict | None = Field(default=None)


class CitationSchema(BaseModel):
    source_label: str
    document_id: str
    filename: str
    page_number: int | None = None
    section_title: str | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    chunk_text: str = ""
    relevance_score: float | None = None


class SourceDocumentSchema(BaseModel):
    document_id: str
    filename: str | None = None
    chunk_text: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    relevance_score: float | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationSchema]
    source_documents: list[SourceDocumentSchema]
    model: str | None = None
    usage: dict | None = None
