from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (BACKEND_ROOT / path).resolve()


class Settings(BaseSettings):
    app_name: str = "Candidate Intelligence Platform"
    database_url: str = "postgresql+psycopg://candidate_app:candidate_app@localhost:5432/candidate_intelligence"
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    seed_file: str = "../data/Dummy Candidate Database 1000 expanded.xlsx"
    cors_origins: str = "http://localhost:3000"
    data_dir: str = "../data"
    upload_dir: str = "../data/uploads"
    pdf_min_characters: int = 80

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return origins if origins else ["http://localhost:3000"]


settings = Settings()
