# Enterprise Document Q&A — RAG with Source Attribution

A full-stack Retrieval-Augmented Generation (RAG) system for asking natural language questions against enterprise documents. Every answer includes inline citations pointing back to the exact source file, page number, and section — so users can verify claims against the originals.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Technology Choices and Rationale](#3-technology-choices-and-rationale)
4. [Project Structure](#4-project-structure)
5. [Backend Deep Dive](#5-backend-deep-dive)
6. [Frontend Deep Dive](#6-frontend-deep-dive)
7. [Data Flow: End to End](#7-data-flow-end-to-end)
8. [Configuration Reference](#8-configuration-reference)
9. [Setup and Running on a New System](#9-setup-and-running-on-a-new-system)
10. [API Reference](#10-api-reference)
11. [Swapping the LLM Provider](#11-swapping-the-llm-provider)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. System Overview

The system has two main workflows:

**Document Ingestion:**
Upload a document (PDF, DOCX, PPTX, XLSX, HTML, Markdown, or TXT) → parse it into text segments with structural metadata (page numbers, section headings, slide numbers, sheet names) → split segments into overlapping chunks → generate vector embeddings → store chunks + embeddings + metadata in ChromaDB.

**Question Answering:**
User asks a question → embed the query → retrieve the top-k most similar chunks from ChromaDB → assemble them into a numbered context (`[SOURCE_1]`, `[SOURCE_2]`, ...) → send context + question to the LLM with a system prompt requiring inline `[SOURCE_N]` citations → parse the response to extract structured citation objects → return the answer with clickable source references in the UI.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Chat Page│  │Documents Page│  │ Settings │  │  Sidebar  │  │
│  │ (Q&A +   │  │ (Upload +   │  │  Page    │  │  + Health │  │
│  │ Citations)│  │  List)      │  │          │  │  Status   │  │
│  └────┬─────┘  └─────┬───────┘  └──────────┘  └───────────┘  │
│       │               │                                        │
│       │ SSE Stream     │ REST                                   │
│       │ (fetch API)    │ (Axios)                                │
└───────┼───────────────┼────────────────────────────────────────┘
        │               │
        │  Vite Dev Proxy: /api → localhost:8000
        │               │
┌───────┼───────────────┼────────────────────────────────────────┐
│       ▼               ▼         FastAPI Backend                │
│  ┌─────────┐   ┌────────────┐                                  │
│  │ /query/ │   │/documents/ │   /health/   /collections/       │
│  │ /stream │   │ /upload    │                                   │
│  └────┬────┘   └─────┬──────┘                                  │
│       │               │                                        │
│  ┌────▼────┐   ┌──────▼───────┐                                │
│  │   RAG   │   │  Ingestion   │                                │
│  │Pipeline │   │  Pipeline    │                                │
│  └────┬────┘   └──────┬───────┘                                │
│       │               │                                        │
│  ┌────┼───────────────┼────┐                                   │
│  │    ▼               ▼    │                                   │
│  │       ChromaStore       │  ← langchain-chroma               │
│  │    (Vector Database)    │                                   │
│  └─────────────────────────┘                                   │
│       │                                                        │
│  ┌────▼─────────────────┐    ┌──────────────────────┐          │
│  │   OllamaEmbeddings   │    │  ChatOllama          │          │
│  │  (nomic-embed-text)  │    │  (gemma2:2b)         │          │
│  └──────────────────────┘    └──────────────────────┘          │
│       ← langchain-ollama →                                     │
└────────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌────────────────────────────────────────────┐
│              Ollama Server                  │
│         http://localhost:11434              │
│  ┌────────────────┐ ┌───────────────────┐  │
│  │ nomic-embed-   │ │    gemma2:2b      │  │
│  │ text (274 MB)  │ │   (1.6 GB)        │  │
│  └────────────────┘ └───────────────────┘  │
└────────────────────────────────────────────┘
```

---

## 3. Technology Choices and Rationale

### 3.1 LLM: Ollama with gemma2:2b

| Choice | Rationale |
|--------|-----------|
| **Ollama** as the inference server | Runs fully offline, no API keys, one-command model download, REST API on localhost |
| **gemma2:2b** as the generation model | Smallest model that can follow structured citation instructions; fast inference on CPU; good for development and internal use |
| **nomic-embed-text** for embeddings | 768-dimensional embeddings, strong retrieval quality for its size (274 MB), optimized for cosine similarity |
| **Provider abstraction layer** | Abstract `LLMProvider` / `EmbeddingProvider` interfaces let you swap to Claude, OpenAI, or Azure by changing one env var — no code changes needed |

### 3.2 LangChain: Selective Integration

LangChain is used in three specific places — not as a full framework, but as a library for well-tested components:

| Component | LangChain Package | Why LangChain Here |
|-----------|-------------------|-------------------|
| **Text splitting** | `langchain-text-splitters` | `RecursiveCharacterTextSplitter` handles Unicode, multi-separator fallback, and automatic metadata propagation to child chunks. Writing our own would replicate 500+ lines of edge-case handling. |
| **Ollama integration** | `langchain-ollama` | `ChatOllama` and `OllamaEmbeddings` provide clean async generate/stream/embed methods with proper error handling and connection pooling. |
| **ChromaDB vector store** | `langchain-chroma` | `Chroma` wraps embedding + storage into a single `add_documents()` call and provides `similarity_search_with_score()` with metadata filtering. |

**Where LangChain is NOT used (and why):**

| Component | Why Custom |
|-----------|-----------|
| **Document parsers** | LangChain's document loaders (`PyPDFLoader`, `Docx2txtLoader`, etc.) flatten everything into plain text and lose page-level / slide-level / sheet-level metadata. Our parsers preserve `page_number`, `section_title`, `slide_number`, and `sheet_name` per text segment — this metadata powers source attribution. |
| **RAG chain** | LangChain's `RetrievalQA` and LCEL chains don't support our `[SOURCE_N]` citation format with structured citation parsing. We need fine-grained control over context assembly, prompt construction, and response parsing. |
| **LLM abstraction** | Our own `LLMProvider` interface is simpler than LangChain's `BaseLLM` / `BaseChatModel` hierarchy. It has exactly three methods (`generate`, `stream`, `model_name`) and makes provider swapping a one-line config change. |

### 3.3 Vector Database: ChromaDB

| Choice | Rationale |
|--------|-----------|
| **ChromaDB** | Embedded (no separate server), persistent to disk, Python-native, supports metadata filtering and cosine similarity out of the box |
| **Cosine distance** | Standard metric for text embedding models; both `nomic-embed-text` and `sentence-transformers` models are trained with cosine objectives |
| **Collection-based isolation** | Each collection is a separate namespace, allowing users to organize documents into logical groups |

### 3.4 Document Parsing Libraries

| Format | Library | Why This One |
|--------|---------|-------------|
| PDF | **PyMuPDF** (`fitz`) | Provides font-size metadata per text span, enabling heading detection by font size (≥14pt → section title). 3-10x faster than PyPDF2. Active maintenance. |
| DOCX | **python-docx** | Exposes paragraph styles (`Heading 1`, `Heading 2`), enabling section title extraction from Word's heading hierarchy. |
| PPTX | **python-pptx** | Only maintained PPTX parser for Python. Extracts text per shape per slide, preserves slide titles. |
| XLSX | **openpyxl** | Read-only mode for large files. Extracts row-by-row with sheet name metadata. |
| HTML | **beautifulsoup4** + **lxml** | BS4 for DOM traversal and semantic tag extraction (`h1`-`h6`, `p`, `li`). lxml as the fast parser backend. |
| Markdown | **markdown-it-py** | Parses to AST tokens, allowing heading extraction from `heading_open` tokens rather than fragile regex. |
| TXT | Built-in + **chardet** | `chardet` auto-detects encoding (UTF-8, Latin-1, etc.) so non-Unicode files don't break. |

### 3.5 Backend: FastAPI

| Choice | Rationale |
|--------|-----------|
| **FastAPI** | Native async support (needed for Ollama API calls and SSE streaming), automatic OpenAPI docs at `/docs`, Pydantic integration for request/response validation, dependency injection |
| **SSE** via `sse-starlette` | Server-Sent Events for streaming LLM responses; simpler than WebSocket for unidirectional server→client data; works over standard HTTP |
| **pydantic-settings** | Type-safe configuration from env vars with validation, `.env` file support, and `RAG_` prefix to avoid collisions |

### 3.6 Frontend: React + TypeScript + Vite

| Choice | Rationale |
|--------|-----------|
| **Vite** | Sub-second HMR, native TypeScript support, built-in dev proxy to backend |
| **TailwindCSS** | Utility-first CSS; no heavy UI framework needed for 3 pages and ~15 components |
| **TanStack Query** | Server state management for documents/collections/health: automatic caching, refetching, and loading/error states |
| **Zustand** | Client-only state (chat messages) doesn't need server cache semantics; Zustand is minimal and has no provider nesting |
| **Native `fetch`** for SSE | `EventSource` API only supports GET; our streaming endpoint is POST, so we use `fetch` with `ReadableStream` |
| **No heavy UI library** | Tailwind + hand-built components (`Button`, `Card`, `Badge`) is lighter than Material UI / Ant Design for an internal tool |

### 3.7 Chunking Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `chunk_size` | 2048 characters (~512 tokens) | Sweet spot for retrieval quality with embedding models that have 512-token context windows |
| `chunk_overlap` | 256 characters (~64 tokens) | Prevents information loss at chunk boundaries without excessive duplication |
| Separators | `["\n\n", "\n", ". ", " ", ""]` | Recursive fallback: prefer paragraph breaks, then line breaks, then sentence boundaries, then words |

### 3.8 Citation Format Design

The `[SOURCE_N]` inline reference format was chosen because:
- LLMs can reliably follow it (simpler than footnote or parenthetical styles)
- Easy to parse with a single regex: `/\[SOURCE_(\d+)\]/g`
- Unambiguous — no collision with natural text
- The `ANSWER:` / `SOURCES:` section split in the LLM output provides a reliable parsing boundary

---

## 4. Project Structure

```
RAG_proj/
│
├── pyproject.toml              # Python package metadata and dependencies
├── requirements.txt            # Flat dependency list (alternative to pyproject.toml)
├── .env.example                # Template for environment variables
├── .env                        # Active config (gitignored, copy from .env.example)
├── .gitignore
│
├── config/
│   └── prompts/
│       └── rag_system.txt      # LLM system prompt with citation instructions
│
├── src/                        # ─── PYTHON BACKEND ───
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory, lifespan, exception handlers
│   ├── dependencies.py         # FastAPI dependency injection functions
│   │
│   ├── core/
│   │   ├── config.py           # Settings class (pydantic-settings, RAG_ env prefix)
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   └── logging.py          # Structured logging setup
│   │
│   ├── api/
│   │   ├── router.py           # Top-level router aggregator
│   │   └── v1/
│   │       ├── documents.py    # Upload, list, delete endpoints
│   │       ├── query.py        # Sync Q&A + SSE streaming endpoints
│   │       ├── collections.py  # Collection listing endpoint
│   │       └── health.py       # Health check endpoint
│   │
│   ├── schemas/
│   │   ├── documents.py        # Pydantic models for document operations
│   │   ├── query.py            # Pydantic models for Q&A request/response
│   │   └── common.py           # Health response, error response
│   │
│   ├── ingestion/
│   │   ├── pipeline.py         # Ingestion orchestrator: parse → chunk → embed → store
│   │   └── parsers/
│   │       ├── base.py         # BaseParser ABC + ParsedSegment dataclass
│   │       ├── pdf_parser.py   # PyMuPDF with font-size heading detection
│   │       ├── docx_parser.py  # python-docx with heading style detection
│   │       ├── pptx_parser.py  # python-pptx with slide title extraction
│   │       ├── xlsx_parser.py  # openpyxl with sheet name tracking
│   │       ├── html_parser.py  # BS4 with semantic tag extraction
│   │       ├── markdown_parser.py  # markdown-it-py AST-based parsing
│   │       ├── text_parser.py  # chardet encoding detection
│   │       └── registry.py     # Maps file extension → parser instance
│   │
│   ├── llm/
│   │   ├── base.py             # Abstract LLMProvider + EmbeddingProvider
│   │   ├── factory.py          # Creates provider from config ("ollama" | "claude" | "openai")
│   │   └── providers/
│   │       ├── ollama.py       # langchain_ollama.ChatOllama + OllamaEmbeddings
│   │       ├── claude.py       # Stub (NotImplementedError)
│   │       └── openai_provider.py  # Stub (NotImplementedError)
│   │
│   ├── rag/
│   │   ├── retriever.py        # ChromaDB similarity search wrapper
│   │   ├── context_builder.py  # Assembles [SOURCE_N]-labeled context + source_map
│   │   ├── citation_parser.py  # Regex-extracts citations from LLM output
│   │   └── pipeline.py         # End-to-end: retrieve → build context → generate → parse
│   │
│   ├── vectorstore/
│   │   └── chroma_store.py     # langchain-chroma wrapper with collection management
│   │
│   └── storage/
│       └── file_store.py       # Raw uploaded file storage on local filesystem
│
├── frontend/                   # ─── REACT FRONTEND ───
│   ├── package.json
│   ├── vite.config.ts          # Dev proxy: /api → localhost:8000
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx            # React entry: QueryClient + Router + Toaster
│       ├── index.css           # Tailwind directives + btn-primary/secondary/danger
│       ├── vite-env.d.ts       # Vite type declarations
│       │
│       ├── types/
│       │   ├── api.ts          # TypeScript interfaces matching backend schemas
│       │   └── ui.ts           # ChatMessage, AnswerSegment types
│       │
│       ├── api/
│       │   ├── client.ts       # Axios instance (baseURL: /api/v1)
│       │   ├── documents.ts    # uploadDocument, listDocuments, deleteDocument
│       │   ├── query.ts        # queryDocuments, getStreamUrl
│       │   └── health.ts       # getHealth, getCollections
│       │
│       ├── hooks/
│       │   └── useQueryStream.ts   # SSE streaming hook (fetch + ReadableStream)
│       │
│       ├── lib/
│       │   ├── citationParser.ts   # parseAnswer: text → AnswerSegment[]
│       │   └── formatters.ts       # formatFileSize, formatDate, formatScore
│       │
│       ├── store/
│       │   └── chatStore.ts    # Zustand: messages[], activeCollection, add/update/clear
│       │
│       ├── router/
│       │   └── index.tsx       # 3 routes: /, /documents, /settings
│       │
│       └── components/
│           ├── layout/
│           │   ├── AppShell.tsx     # Sidebar + <Outlet> grid layout
│           │   ├── Sidebar.tsx      # Navigation + health indicator
│           │   └── MobileNav.tsx    # Responsive hamburger menu
│           │
│           ├── chat/
│           │   ├── ChatPage.tsx     # Message list + input + streaming
│           │   ├── ChatInput.tsx    # Textarea with Enter/Shift+Enter handling
│           │   ├── MessageBubble.tsx # User/assistant message rendering
│           │   ├── AnswerContent.tsx # Parses answer → text spans + CitationChips
│           │   ├── CitationChip.tsx  # Clickable [N] badge (inline)
│           │   └── CitationDetail.tsx # Expanded source: file, page, section, text
│           │
│           ├── documents/
│           │   ├── DocumentsPage.tsx # Upload zone + document list
│           │   ├── UploadZone.tsx    # Drag-and-drop with react-dropzone
│           │   └── DocumentList.tsx  # Table with type badges, delete
│           │
│           └── settings/
│               └── SettingsPage.tsx  # Collection selector, model info, system status
│
├── tests/                      # ─── TESTS ───
│   ├── conftest.py             # (placeholder)
│   ├── test_parsers/           # Unit tests for document parsers
│   ├── test_api/               # API integration tests
│   └── fixtures/               # Sample documents for testing
│
└── data/                       # ─── RUNTIME DATA (gitignored) ───
    ├── uploads/                # Raw uploaded files, organized by document_id
    └── chroma_db/              # ChromaDB persistent storage
```

---

## 5. Backend Deep Dive

### 5.1 Application Lifecycle (`src/main.py`)

The FastAPI app uses a `lifespan` context manager to initialize all components at startup:

1. Load `Settings` from `.env` file and environment variables
2. Create `OllamaLLMProvider` (wraps `ChatOllama`) and `OllamaEmbeddingProvider` (wraps `OllamaEmbeddings`)
3. Create `ChromaStore` with the embedding provider's LangChain embeddings object
4. Register all 7 document parsers via `ParserRegistry.register_defaults()`
5. Create `FileStore` for raw file storage
6. Create `IngestionPipeline` (ties parsers + splitter + vector store + file store)
7. Create `RAGPipeline` (ties retriever + context builder + LLM + citation parser + system prompt)
8. Attach all components to `app.state` for dependency injection

CORS is configured to allow requests from `http://localhost:5173` (Vite dev server) and `http://localhost:3000`.

### 5.2 Document Parsers (`src/ingestion/parsers/`)

Every parser extends `BaseParser` and implements:
- `supported_extensions()` → list of file extensions it handles
- `parse(file_path)` → list of `ParsedSegment` objects

A `ParsedSegment` carries:
```python
@dataclass
class ParsedSegment:
    text: str                          # The extracted text content
    page_number: int | None = None     # 1-indexed page (PDF)
    section_title: str | None = None   # Nearest heading
    paragraph_index: int | None = None # Position within page/section
    sheet_name: str | None = None      # Sheet name (XLSX)
    slide_number: int | None = None    # Slide number (PPTX)
```

**PDF heading detection**: The PDF parser uses PyMuPDF's `get_text("dict")` to access font-size per text span. Text blocks where the largest span font size is ≥14pt and text length is <200 characters are classified as section headings. This heuristic works well for typical enterprise documents with standard formatting.

**Parser Registry**: A dictionary mapping file extension → parser instance. `register_defaults()` registers all 7 built-in parsers. Custom parsers can be added by subclassing `BaseParser` and calling `registry.register(MyParser())`.

### 5.3 Ingestion Pipeline (`src/ingestion/pipeline.py`)

The `IngestionPipeline.ingest()` method orchestrates the full document processing flow:

1. **Store raw file**: Copy uploaded file to `data/uploads/{document_id}/{filename}`
2. **Parse**: Select the appropriate parser via the registry, extract `ParsedSegment` list
3. **Convert to LangChain Documents**: Each segment becomes a `langchain_core.documents.Document` with metadata dict (`document_id`, `filename`, `doc_type`, `page_number`, `section_title`, etc.)
4. **Split**: `RecursiveCharacterTextSplitter.split_documents()` chunks the documents while auto-propagating metadata to each child chunk
5. **Index chunks**: Add `chunk_index` and `chunk_count` to each chunk's metadata
6. **Embed + Store**: `ChromaStore.add_documents()` generates embeddings via Ollama and stores everything in ChromaDB

If any step fails after the file is stored, the file is cleaned up (`file_store.delete(document_id)`).

### 5.4 RAG Pipeline (`src/rag/pipeline.py`)

The `RAGPipeline` has two modes:

**Synchronous (`query()`):**
1. `ChromaRetriever.retrieve()` → embed query, search ChromaDB, return `RetrievedChunk` list with scores
2. `ContextBuilder.build()` → format chunks as numbered sources with location metadata, return context string + source_map
3. Send `CONTEXT + QUESTION` to the LLM with the system prompt from `config/prompts/rag_system.txt`
4. `CitationParser.parse()` → split response at `SOURCES:` boundary, regex-extract `[SOURCE_N]` references, map to `Citation` objects
5. Return `QueryResponse` with answer, citations, source_documents, model, usage

**Streaming (`query_stream()`):**
1-2 are identical. Then:
3. Stream tokens from the LLM via `ChatOllama.astream()`, yielding each token as a `{"type": "token", "data": "..."}` JSON event
4. After streaming completes, parse the accumulated text for citations and yield a `{"type": "citations", "data": [...]}` event
5. Yield a `{"type": "done", "data": null}` terminal event

### 5.5 Context Builder (`src/rag/context_builder.py`)

Transforms retrieved chunks into a structured context string the LLM can reference:

```
[SOURCE_1] (File: report.pdf | Page: 5 | Section: Executive Summary)
The company reported a 15% increase in revenue...

---
[SOURCE_2] (File: report.pdf | Page: 12 | Section: Financial Outlook)
Projected growth for Q3 is estimated at...
```

Also builds a `source_map` — a list of dicts mapping each source index to its full metadata. This source_map is used after LLM generation to convert `[SOURCE_N]` references in the answer into structured `Citation` objects with file, page, section, and chunk text.

### 5.6 Citation Parser (`src/rag/citation_parser.py`)

Uses regex `\[SOURCE_(\d+)\]` to find all cited source indices in the answer text. Cross-references them against the source_map to produce `Citation` dataclass instances with:
- `source_label`: e.g., `[SOURCE_1]`
- `document_id`, `filename`: which document
- `page_number`, `section_title`, `slide_number`, `sheet_name`: where in the document
- `chunk_text`: the actual source text chunk
- `relevance_score`: cosine distance from the query

### 5.7 Vector Store (`src/vectorstore/chroma_store.py`)

Wraps `langchain_chroma.Chroma` with collection management helpers:
- `add_documents()`: Embed and store chunks with IDs formatted as `{document_id}_{chunk_index}`
- `similarity_search_with_score()`: Query by text with optional metadata filter
- `delete_by_document_id()`: Remove all chunks belonging to a document (uses ChromaDB's `where` filter)
- `list_documents()`: Aggregate chunk metadata to return unique document entries
- `list_collections()` / `collection_count()`: Collection inventory

Collections use `{"hnsw:space": "cosine"}` for cosine similarity indexing.

### 5.8 Dependency Injection (`src/dependencies.py`)

All pipeline components are accessed via FastAPI's `Depends()` mechanism. Functions like `get_rag_pipeline(request)` extract the component from `request.app.state`, keeping endpoint code clean.

---

## 6. Frontend Deep Dive

### 6.1 Application Entry (`src/main.tsx`)

Sets up three providers:
- `QueryClientProvider` — TanStack Query with retry=1, no refetch-on-focus
- `RouterProvider` — React Router with 3 routes under `AppShell`
- `Toaster` — react-hot-toast for notifications (bottom-right)

### 6.2 Routing

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | `ChatPage` | Main Q&A interface |
| `/documents` | `DocumentsPage` | Upload and manage documents |
| `/settings` | `SettingsPage` | Collection selection, model info, system status |

All routes render inside `AppShell`, which provides the sidebar (desktop) or hamburger menu (mobile).

### 6.3 Chat Page — How Citation Highlighting Works

This is the core UI feature. The flow is:

**Step 1: Stream the answer**
`useQueryStream` hook sends a POST to `/api/v1/query/stream` via native `fetch`. It reads the SSE response chunk-by-chunk:
- `token` events: Append to the accumulated answer text, update the Zustand message
- `citations` event: Store the structured citation array
- `done` event: Mark the message as complete

**Step 2: Parse the answer text**
`citationParser.ts` is a pure function that splits the answer at `[SOURCE_N]` boundaries:
```
Input:  "Revenue grew 15% [SOURCE_1] driven by new products [SOURCE_2]."
Output: [
  { type: "text", value: "Revenue grew 15% " },
  { type: "citation", label: "[SOURCE_1]", index: 0 },
  { type: "text", value: " driven by new products " },
  { type: "citation", label: "[SOURCE_2]", index: 1 },
  { type: "text", value: "." }
]
```

During streaming, partial tokens like `[SOURCE_` don't match the regex and stay as plain text until the closing `]` arrives.

**Step 3: Render with interactive chips**
`AnswerContent` maps segments to `<span>` elements (text) and `CitationChip` buttons (citations). Chips are styled as small numbered badges. Clicking a chip toggles `CitationDetail` — a card showing:
- Filename + page number
- Section title
- The source chunk text (indented with a left border accent)
- Relevance score percentage

Only one citation can be expanded at a time (accordion pattern).

### 6.4 Documents Page

- `UploadZone`: `react-dropzone` with accepted MIME types for all 7 formats, 50MB size limit. Files are uploaded via `POST /api/v1/documents/upload` with multipart form data. Axios `onUploadProgress` could be wired for progress bars.
- `DocumentList`: TanStack Query polls `GET /api/v1/documents/` every 10 seconds. Shows a table with filename, type badge (color-coded by format), chunk count, and upload date. Delete requires a double-click confirmation (click once to arm, click again within 3 seconds to confirm).

### 6.5 Settings Page

- **Active Collection**: Dropdown populated from `GET /api/v1/collections/`. Persisted to `localStorage` via Zustand so it survives page reloads.
- **Model Information**: Displays LLM provider/model and embedding provider/model from `GET /api/v1/health/`.
- **System Status**: Health status dot (green/red), version, total chunks, collection count.
- **Clear Chat**: Resets the Zustand message array.

### 6.6 State Management

| Concern | Tool | Why |
|---------|------|-----|
| Documents list, collections, health | TanStack Query | Server-derived state with caching and automatic refetching |
| Chat messages | Zustand | Session-only client state; doesn't need server cache semantics |
| Active collection | Zustand + `localStorage` | Persists across page reloads |
| Expanded citation | React `useState` | Component-local, ephemeral |

---

## 7. Data Flow: End to End

### 7.1 Document Upload Flow

```
User drops "report.pdf" on UploadZone
    │
    ▼
Frontend: POST /api/v1/documents/upload (multipart: file + collection_name)
    │
    ▼
Backend: documents.py endpoint
    ├── Validate extension (.pdf ∈ allowed set)
    ├── Check file size (< 50MB)
    ├── Write to temp file
    │
    ▼
IngestionPipeline.ingest()
    ├── FileStore.store()           → data/uploads/{uuid}/report.pdf
    ├── PDFParser.parse()           → [ParsedSegment(text="...", page_number=1, section_title="Intro"), ...]
    ├── Convert to LangChain Documents with metadata dicts
    ├── RecursiveCharacterTextSplitter.split_documents()  → chunked Documents with inherited metadata
    ├── Add chunk_index/chunk_count to each chunk's metadata
    └── ChromaStore.add_documents() → OllamaEmbeddings → ChromaDB upsert
    │
    ▼
Response: { document_id: "uuid", filename: "report.pdf", chunk_count: 42, ... }
    │
    ▼
Frontend: Toast "Uploaded report.pdf (42 chunks)" + invalidate document list query
```

### 7.2 Question Answering Flow (Streaming)

```
User types "What was Q3 revenue?" and presses Enter
    │
    ▼
Frontend: useQueryStream → fetch POST /api/v1/query/stream
    │
    ▼
Backend: query.py stream endpoint → RAGPipeline.query_stream()
    │
    ├── ChromaRetriever.retrieve()
    │   ├── OllamaEmbeddings.aembed_query("What was Q3 revenue?")
    │   └── ChromaDB similarity_search_with_score(embedding, k=5)
    │   └── Returns: [(Document, 0.23), (Document, 0.31), ...]
    │
    ├── ContextBuilder.build()
    │   └── "[SOURCE_1] (File: report.pdf | Page: 12 | Section: Q3 Results)\n..."
    │   └── source_map: [{source_index: 1, filename: "report.pdf", page_number: 12, ...}, ...]
    │
    ├── ChatOllama.astream(system_prompt + context + question)
    │   └── Yields tokens: "ANSWER", ":", "\n", "Q3", " revenue", " was", ...
    │   └── Each token → SSE event: data: {"type": "token", "data": "Q3"}
    │
    ├── CitationParser.parse(accumulated_response, source_map)
    │   └── Extracts: answer text + [Citation(source_label="[SOURCE_1]", ...)]
    │   └── SSE event: data: {"type": "citations", "data": [...]}
    │
    └── SSE event: data: {"type": "done", "data": null}
    │
    ▼
Frontend: useQueryStream processes each SSE event
    ├── "token" → append to message content, re-render
    ├── "citations" → store citation array
    └── "done" → mark message as complete, attach citations
    │
    ▼
AnswerContent renders:
    ├── parseAnswer(text) → segments with text spans + citation chips
    ├── CitationChip [1] [2] rendered inline
    └── Click chip → CitationDetail shows source file, page, section, chunk text
```

---

## 8. Configuration Reference

All settings are controlled via environment variables with the `RAG_` prefix. Defaults are defined in `src/core/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_DEBUG` | `false` | Enable debug mode |
| `RAG_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `RAG_HOST` | `0.0.0.0` | Server bind address |
| `RAG_PORT` | `8000` | Server port |
| `RAG_LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `claude`, or `openai` |
| `RAG_EMBEDDING_PROVIDER` | `ollama` | Embedding provider: `ollama` |
| `RAG_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `RAG_OLLAMA_LLM_MODEL` | `gemma2:2b` | Ollama generation model |
| `RAG_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `RAG_CLAUDE_API_KEY` | (none) | Anthropic API key (for Claude provider) |
| `RAG_CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model ID |
| `RAG_OPENAI_API_KEY` | (none) | OpenAI API key |
| `RAG_OPENAI_MODEL` | `gpt-4o` | OpenAI model ID |
| `RAG_CHROMA_PERSIST_DIR` | `./data/chroma_db` | ChromaDB storage path |
| `RAG_UPLOAD_DIR` | `./data/uploads` | Uploaded file storage path |
| `RAG_MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload file size in MB |
| `RAG_CHUNK_SIZE` | `2048` | Text chunk size in characters |
| `RAG_CHUNK_OVERLAP` | `256` | Overlap between chunks in characters |
| `RAG_DEFAULT_TOP_K` | `5` | Default number of chunks to retrieve |
| `RAG_DEFAULT_TEMPERATURE` | `0.1` | Default LLM temperature |
| `RAG_DEFAULT_COLLECTION` | `default` | Default ChromaDB collection name |
| `RAG_PROMPTS_DIR` | `./config/prompts` | Directory for prompt template files |

---

## 9. Setup and Running on a New System

### 9.1 Prerequisites

Install these three things first:

| Software | Minimum Version | Install From |
|----------|----------------|-------------|
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) or `pyenv install 3.11` |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) or `nvm install 18` |
| **Ollama** | Latest | [ollama.com](https://ollama.com/) (one-click installer for Windows/Mac/Linux) |

### 9.2 Step-by-Step Instructions

**Step 1: Transfer the project**

Copy the entire `RAG_proj/` folder to the new system. You can skip these directories — they'll be recreated:
- `frontend/node_modules/` (recreated by `npm install`)
- `frontend/dist/` (recreated by `npm run build`)
- `data/uploads/` (created at runtime)
- `data/chroma_db/` (created at runtime)
- `__pycache__/` directories

**Step 2: Create a Python virtual environment and install dependencies**

```bash
cd RAG_proj

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install dependencies (use ONE of these):
pip install -r requirements.txt
# OR:
pip install -e .
```

**Step 3: Create the `.env` file**

```bash
cp .env.example .env
```

The defaults in `.env.example` are ready to use — no changes needed unless Ollama runs on a different host.

**Step 4: Download the Ollama models**

Make sure the Ollama application is running (it starts a background server), then:

```bash
ollama pull gemma2:2b
ollama pull nomic-embed-text
```

`gemma2:2b` is ~1.6 GB and `nomic-embed-text` is ~274 MB. These only download once.

Verify Ollama is serving:
```bash
curl http://localhost:11434/api/tags
```

You should see both models listed.

**Step 5: Start the backend**

```bash
cd RAG_proj
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running: open `http://localhost:8000/docs` in a browser — you should see the FastAPI Swagger UI.

**Step 6: Install frontend dependencies and start the dev server**

Open a **second terminal**:

```bash
cd RAG_proj/frontend
npm install
npm run dev
```

**Step 7: Open the application**

Open `http://localhost:5173` in your browser.

- Go to the **Documents** tab, upload a PDF or DOCX
- Go to the **Chat** tab, ask a question
- Click the numbered citation badges in the answer to see source details

### 9.3 Files You May Need to Change

| File | When to Change | What to Change |
|------|---------------|----------------|
| `.env` | If Ollama runs on a different machine | Change `RAG_OLLAMA_BASE_URL` to `http://<host>:11434` |
| `.env` | If you want a different model | Change `RAG_OLLAMA_LLM_MODEL` (e.g., `llama3.1:8b`, `mistral:7b`) |
| `.env` | If you want larger/smaller chunks | Adjust `RAG_CHUNK_SIZE` and `RAG_CHUNK_OVERLAP` |
| `src/main.py` (line 79) | If the frontend runs on a different port or host | Add the origin URL to `allow_origins` list |
| `frontend/vite.config.ts` (line 13) | If the backend runs on a different port | Change `target` in the proxy config |

**For a standard single-machine setup with defaults, you don't need to change any files.**

---

## 10. API Reference

Base URL: `http://localhost:8000/api/v1`

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload a single document (multipart form: `file` + `collection_name`) |
| `POST` | `/documents/upload/batch` | Upload multiple documents at once |
| `GET` | `/documents/?collection_name=default` | List all documents in a collection |
| `DELETE` | `/documents/{document_id}?collection_name=default` | Delete a document and all its chunks |

### Query

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query/` | Synchronous Q&A — returns full answer with citations |
| `POST` | `/query/stream` | SSE streaming — returns token-by-token with final citations event |

**Query request body:**
```json
{
  "question": "What was Q3 revenue?",
  "collection_name": "default",
  "top_k": 5,
  "temperature": 0.1,
  "metadata_filter": null
}
```

**Query response:**
```json
{
  "answer": "Q3 revenue was $2.1M [SOURCE_1], representing a 15% increase [SOURCE_2].",
  "citations": [
    {
      "source_label": "[SOURCE_1]",
      "document_id": "uuid",
      "filename": "report.pdf",
      "page_number": 12,
      "section_title": "Q3 Results",
      "chunk_text": "The company reported Q3 revenue of $2.1 million...",
      "relevance_score": 0.23
    }
  ],
  "source_documents": [...],
  "model": "gemma2:2b",
  "usage": {"prompt_tokens": 1200, "completion_tokens": 350}
}
```

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health/` | System health with model info and document count |
| `GET` | `/collections/` | List all collections with document counts |

Interactive API docs are available at `http://localhost:8000/docs` (Swagger UI).

---

## 11. Swapping the LLM Provider

The system is designed for provider swapping without code changes.

### Switch to a different Ollama model

Edit `.env`:
```
RAG_OLLAMA_LLM_MODEL=llama3.1:8b
```
Then pull the model: `ollama pull llama3.1:8b` and restart the backend.

### Switch to Claude (future)

1. Install: `pip install anthropic` (or `pip install -e ".[claude]"`)
2. Implement `ClaudeLLMProvider` in `src/llm/providers/claude.py` (replace the `NotImplementedError` stub)
3. Edit `.env`:
   ```
   RAG_LLM_PROVIDER=claude
   RAG_CLAUDE_API_KEY=sk-ant-...
   RAG_CLAUDE_MODEL=claude-sonnet-4-20250514
   ```
4. Restart the backend.

### Switch to OpenAI (future)

1. Install: `pip install openai` (or `pip install -e ".[openai]"`)
2. Implement `OpenAILLMProvider` in `src/llm/providers/openai_provider.py`
3. Edit `.env`:
   ```
   RAG_LLM_PROVIDER=openai
   RAG_OPENAI_API_KEY=sk-...
   RAG_OPENAI_MODEL=gpt-4o
   ```
4. Restart the backend.

The embedding provider can be swapped independently — you could use OpenAI embeddings with Ollama generation, or vice versa.

---

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Backend fails to start with "Connection refused" | Ollama not running | Start the Ollama application, then verify with `curl http://localhost:11434/api/tags` |
| "Model not found" error | Ollama model not downloaded | Run `ollama pull gemma2:2b` and `ollama pull nomic-embed-text` |
| Frontend shows "Disconnected" health status | Backend not running or CORS issue | Start backend with `uvicorn src.main:app --reload`, check terminal for errors |
| Upload fails with 415 error | Unsupported file type | Only PDF, DOCX, PPTX, XLSX, HTML, MD, TXT are supported |
| Upload fails with 413 error | File too large | Default max is 50MB; change `RAG_MAX_UPLOAD_SIZE_MB` in `.env` |
| Answers don't cite sources | Model too small for citation format | Try a larger model: `ollama pull llama3.1:8b`, update `.env` |
| `pip install` fails on corporate network | Package registry blocked | Configure pip to use your organization's package mirror (e.g., JFrog Artifactory) |
| `ModuleNotFoundError: No module named 'src'` | Package not installed or wrong working directory | Run `pip install -e .` from the project root, or ensure you're running `uvicorn` from the `RAG_proj/` directory |
| ChromaDB errors about SQLite version | System SQLite too old (< 3.35) | Install `pysqlite3-binary` and add the chromadb SQLite workaround, or upgrade your system SQLite |
