class RAGBaseError(Exception):
    pass


class UnsupportedFormatError(RAGBaseError):
    pass


class DocumentNotFoundError(RAGBaseError):
    pass


class LLMProviderError(RAGBaseError):
    pass


class EmbeddingError(RAGBaseError):
    pass


class IngestionError(RAGBaseError):
    pass


class VectorStoreError(RAGBaseError):
    pass


class FileTooLargeError(RAGBaseError):
    pass
