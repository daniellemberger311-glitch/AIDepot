from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    marketaux_api_key: str = ""
    simfin_api_key: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    sqlite_db_path: str = "./data/aidepot.db"

    scan_hour_utc: int = 6
    scan_minute_utc: int = 0

    finnhub_calls_per_minute: int = 60
    alpha_vantage_calls_per_day: int = 25
    marketaux_calls_per_day: int = 100

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_port: int = 5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def db_path(self) -> Path:
        p = Path(self.sqlite_db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
