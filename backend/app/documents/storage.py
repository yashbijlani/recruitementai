from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.core.config import resolve_path, settings


class DocumentStorage:
    def save(self, filename: str, content: bytes) -> str:
        raise NotImplementedError

    @contextmanager
    def temporary_path(self, key: str):
        raise NotImplementedError


class LocalFileStorage(DocumentStorage):
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

    @contextmanager
    def temporary_path(self, key: str):
        yield self.path(key)


class SupabaseStorage(DocumentStorage):
    def __init__(self, url: str, service_role_key: str, bucket: str = settings.storage_bucket):
        self.base_url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {service_role_key}", "apikey": service_role_key}
        self.bucket = bucket

    def _object_url(self, key: str) -> str:
        encoded_key = quote(key, safe="/")
        return f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_key}"

    def save(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.casefold()
        key = f"{uuid4().hex}{suffix}"
        response = httpx.post(self._object_url(key), content=content, headers={**self.headers, "Content-Type": "application/octet-stream"}, timeout=30)
        response.raise_for_status()
        return key

    @contextmanager
    def temporary_path(self, key: str):
        response = httpx.get(self._object_url(key), headers=self.headers, timeout=60)
        response.raise_for_status()
        suffix = Path(key).suffix
        temporary = NamedTemporaryFile(prefix="candidate-cv-", suffix=suffix, delete=False)
        try:
            temporary.write(response.content)
            temporary.close()
            yield Path(temporary.name)
        finally:
            Path(temporary.name).unlink(missing_ok=True)

    def delete(self, key: str) -> None:
        response = httpx.delete(self._object_url(key), headers=self.headers, timeout=30)
        response.raise_for_status()


def get_storage() -> DocumentStorage:
    if settings.storage_backend.casefold() == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase Storage")
        return SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
    if settings.storage_backend.casefold() == "local":
        return LocalFileStorage()
    raise RuntimeError(f"Unsupported STORAGE_BACKEND: {settings.storage_backend}")
