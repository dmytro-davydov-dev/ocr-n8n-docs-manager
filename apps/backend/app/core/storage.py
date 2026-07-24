import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class StoredFile:
    storage_path: str
    size_bytes: int
    content_hash: str


class LocalDocumentStorage:
    """Filesystem storage on the shared `documents` volume (ADR-006: binaries
    live outside PostgreSQL, referenced by path)."""

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.documents_storage_path)

    def save(self, document_id: str, filename: str, content: bytes) -> StoredFile:
        directory = self.root / document_id
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / filename

        destination.write_bytes(content)

        return StoredFile(
            storage_path=str(destination),
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest(),
        )

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def exists(self, storage_path: str) -> bool:
        return Path(storage_path).exists()


storage = LocalDocumentStorage()
