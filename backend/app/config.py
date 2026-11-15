from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
WORKSPACES_DIR = BASE_DIR.parent / "rfp_workspaces"
WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    llm_api_key: str = ""
    llm_base_url: str = "https://openai.com"
    llm_model: str = "gpt-4o-mini"
    host: str = "0.0.0.0"
    port: int = 8000
    corporate_user_default: str = "analyst@corp.local"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
