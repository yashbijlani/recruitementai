from pathlib import Path

import pytest

from app.core.config import Settings
from app.documents.storage import LocalFileStorage, SupabaseStorage, get_storage


def test_supabase_storage_does_not_require_local_filesystem(tmp_path: Path):
    storage = SupabaseStorage("https://example.supabase.co", "server-only-key")
    assert not (tmp_path / "uploads").exists()
    assert storage._object_url("folder/resume file.pdf") == "https://example.supabase.co/storage/v1/object/candidate-cvs/folder/resume%20file.pdf"


def test_local_storage_remains_explicit(tmp_path: Path):
    settings = Settings(upload_dir=str(tmp_path / "uploads"))
    storage = LocalFileStorage(settings.upload_dir)
    key = storage.save("resume.pdf", b"resume")
    with storage.temporary_path(key) as path:
        assert path.read_bytes() == b"resume"


def test_get_storage_selects_supabase_without_local_filesystem(monkeypatch):
    monkeypatch.setattr("app.documents.storage.settings", Settings(
        storage_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="server-only-key",
    ))

    storage = get_storage()

    assert isinstance(storage, SupabaseStorage)
    assert storage.bucket == "candidate-cvs"


def test_get_storage_does_not_fallback_when_supabase_is_misconfigured(monkeypatch):
    monkeypatch.setattr("app.documents.storage.settings", Settings(
        storage_backend="supabase",
        supabase_url="https://example.supabase.co",
    ))

    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        get_storage()