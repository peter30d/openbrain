from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path("/opt/openbrain")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_prefix="OPENBRAIN_",
        extra="ignore",
    )
    env: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8094
    log_level: str = "INFO"

    database_url: str
    archive_dir: str

    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embed_dim: int = 384

    enable_brian_repo: bool = True
    enable_brian_mcp: bool = False

    brian_repo_dir: str = "/opt/openbrain/external/brianmadden-ai"
    brian_site_url: str = "https://brianmadden.ai"
    brian_mcp_url: str = "https://brianmadden.ai/mcp"
    brian_timeout_seconds: int = 20


settings = Settings()  # type: ignore

