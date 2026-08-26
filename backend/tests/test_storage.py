from pathlib import Path

from app.core.config import Settings
from app.documents.storage import LocalFileStorage, SupabaseStorage


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