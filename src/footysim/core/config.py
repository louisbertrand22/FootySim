from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./footysim.db")
    echo_sql: bool = os.getenv("ECHO_SQL", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
