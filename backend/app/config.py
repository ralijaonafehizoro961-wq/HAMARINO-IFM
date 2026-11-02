from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_path: str = './data/ifm.sqlite3'
    admin_api_key: str = ''
    google_factcheck_api_key: str = ''
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    max_upload_bytes: int = 8_388_608
    max_fetch_bytes: int = 1_500_000

@lru_cache
def settings():
    return Settings()
