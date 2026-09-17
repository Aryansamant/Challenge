from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
CORPUS_DIR = KNOWLEDGE_DIR / "corpus"
INDEX_DIR = DATA_DIR / "index"
SESSION_DIR = DATA_DIR / "sessions"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    enable_geo_climate: bool = True
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
