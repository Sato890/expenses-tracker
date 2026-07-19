from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Expenses Manager"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, dotenv_filtering="only_existing"
    )

    database_url: PostgresDsn
