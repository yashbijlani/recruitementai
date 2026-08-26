from pathlib import Path
from uuid import uuid4

from app.core.config import resolve_path, settings


class LocalFileStorage:
    def __init__(self, root: str = settings.upload_dir):
        self.root = resolve_path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.casefold()
        key = f"{uuid4().hex}{suffix}"
        (self.root / key).write_bytes(content)
        return key

    def path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root.resolve() not in candidate.parents:
            raise ValueError("Invalid storage key")
        return candidate
