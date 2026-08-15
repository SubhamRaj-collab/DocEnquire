export interface DocumentMetadata {
  document_id: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
  collection_name: string;
  upload_timestamp: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
  collection_name: string;
  upload_timestamp: string;
  file_size_bytes: number;
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
  total_count: number;
}

export interface DocumentDeleteResponse {
  document_id: string;
  filename: string;
  chunks_deleted: number;
  success: boolean;
}

export interface QueryRequest {
  question: string;
  collection_name?: string;
  top_k?: number;
  temperature?: number;
  metadata_filter?: Record<string, unknown>;
}

export interface Citation {
  source_label: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  section_title: string | null;
  slide_number: number | null;
  sheet_name: string | null;
  chunk_text: string;
  relevance_score: number | null;
}

export interface SourceDocument {
  document_id: string;
  filename: string | null;
  chunk_text: string | null;
  page_number: number | null;
  section_title: string | null;
  relevance_score: number | null;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  source_documents: SourceDocument[];
  model: string | null;
  usage: { prompt_tokens: number; completion_tokens: number } | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string;
  llm_model: string;
  embedding_provider: string;
  embedding_model: string;
  vector_store: string;
  document_count: number;
  collection_count: number;
}

export interface CollectionInfo {
  name: string;
  document_count: number;
}

export interface CollectionsResponse {
  collections: CollectionInfo[];
}
