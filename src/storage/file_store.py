import shutil
from pathlib import Path


class FileStore:
    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def store(self, source_path: str, document_id: str, filename: str) -> str:
        doc_dir = self._base_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        dest = doc_dir / filename
        shutil.copy2(source_path, dest)
        return str(dest)

    def get_path(self, document_id: str, filename: str) -> Path | None:
        path = self._base_dir / document_id / filename
        return path if path.exists() else None

    def delete(self, document_id: str) -> bool:
        doc_dir = self._base_dir / document_id
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
            return True
        return False

    def exists(self, document_id: str) -> bool:
        return (self._base_dir / document_id).exists()
