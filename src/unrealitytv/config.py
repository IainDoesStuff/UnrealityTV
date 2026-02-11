from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    plex_url: str = Field(default="http://localhost:32400", env="PLEX_URL")
    plex_token: str = Field(default="", env="PLEX_TOKEN")
    watch_dir: Path = Field(default=Path("."), env="WATCH_DIR")
    database_path: Path = Field(default=Path("unrealitytv.db"), env="DATABASE_PATH")
    gpu_enabled: bool = Field(default=False, env="GPU_ENABLED")

class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"