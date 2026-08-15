from src.rag.retriever import RetrievedChunk


class ContextBuilder:
    def build(self, chunks: list[RetrievedChunk]) -> tuple[str, list[dict]]:
        seen: set[tuple[str, int]] = set()
        unique_chunks: list[RetrievedChunk] = []
        for c in chunks:
            key = (c.document_id, c.chunk_index)
            if key not in seen:
                seen.add(key)
                unique_chunks.append(c)

        unique_chunks.sort(key=lambda c: (c.document_id, c.chunk_index))

        context_parts = []
        source_map = []

        for idx, chunk in enumerate(unique_chunks, start=1):
            source_label = f"[SOURCE_{idx}]"

            loc_parts = []
            if chunk.metadata.get("filename"):
                loc_parts.append(f"File: {chunk.metadata['filename']}")
            if chunk.metadata.get("page_number"):
                loc_parts.append(f"Page: {chunk.metadata['page_number']}")
            if chunk.metadata.get("section_title"):
                loc_parts.append(f"Section: {chunk.metadata['section_title']}")
            if chunk.metadata.get("slide_number"):
                loc_parts.append(f"Slide: {chunk.metadata['slide_number']}")
            if chunk.metadata.get("sheet_name"):
                loc_parts.append(f"Sheet: {chunk.metadata['sheet_name']}")

            location = " | ".join(loc_parts)
            context_parts.append(f"{source_label} ({location})\n{chunk.text}\n")

            source_map.append(
                {
                    "source_index": idx,
                    "source_label": source_label,
                    "document_id": chunk.document_id,
                    "filename": chunk.metadata.get("filename"),
                    "page_number": chunk.metadata.get("page_number"),
                    "section_title": chunk.metadata.get("section_title"),
                    "slide_number": chunk.metadata.get("slide_number"),
                    "sheet_name": chunk.metadata.get("sheet_name"),
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.text,
                    "relevance_score": chunk.score,
                }
            )

        return "\n---\n".join(context_parts), source_map
