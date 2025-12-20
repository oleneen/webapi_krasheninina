from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CBR_URL: str = "https://www.cbr.ru/scripts/XML_daily.asp"
    FETCH_INTERVAL_SEC: int = 60
    NATS_URL: str = "nats://localhost:4222"
    DATABASE_URL: str = "sqlite+aiosqlite:///./rates.db"

settings = Settings()