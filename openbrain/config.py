from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path("/opt/openbrain")
ENV_FILE = PROJECT_ROOT / ".env"


def _load_env_file(path: Path) -> None:
    """
    Minimal deterministic .env loader so CLI and service behave the same
    even if pydantic's env_file loading differs by environment.
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if (
            len(value) >= 2
            and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"))
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


_load_env_file(ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENBRAIN_",
        extra="ignore",
        case_sensitive=False,
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
