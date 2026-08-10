import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    PORT: int = 8080
    PAGE_CACHE_TIMEOUT: int = 10
    PAGE_TITLE: str = 'Raspberry Pi System Info'
    CPU_ORANGE_TEMP_THRESHOLD: float = 50.0
    CPU_RED_TEMP_THRESHOLD: float = 60.0
    TEXT_GREEN_COLOR: str = "#00FF40"
    TEXT_ORANGE_COLOR: str = "#FF8C00"
    TEXT_RED_COLOR: str = "#CC0000"
    TEXT_DATETIME_FORMAT: str = "%d-%b-%Y, %H : %M : %S"
    LOGS_PATH: Path = Path("logs")
    LOG_FILENAME: str | None = None
    LOG_LEVEL: str = "INFO"
    LOG_MSG_FORMAT: str | None = None
    LOG_DATETIME_FORMAT: str | None = None
    SECRET_KEY: str = "dev-secret-key"

    @classmethod
    def from_env(cls) -> 'AppConfig':
        load_dotenv('.env')
        secret_key = os.getenv("SECRET_KEY")
        if secret_key is None:
            secret_key = secrets.token_hex(32)
        return cls(
            PORT=int(os.getenv("PORT", cls.PORT)),
            PAGE_CACHE_TIMEOUT=int(os.getenv("PAGE_CACHE_TIMEOUT", cls.PAGE_CACHE_TIMEOUT)),
            PAGE_TITLE=os.getenv("PAGE_TITLE", cls.PAGE_TITLE),
            CPU_ORANGE_TEMP_THRESHOLD=float(os.getenv("CPU_ORANGE_TEMP_THRESHOLD", cls.CPU_ORANGE_TEMP_THRESHOLD)),
            CPU_RED_TEMP_THRESHOLD=float(os.getenv("CPU_RED_TEMP_THRESHOLD", cls.CPU_RED_TEMP_THRESHOLD)),
            TEXT_GREEN_COLOR=os.getenv("TEXT_GREEN_COLOR", cls.TEXT_GREEN_COLOR),
            TEXT_ORANGE_COLOR=os.getenv("TEXT_ORANGE_COLOR", cls.TEXT_ORANGE_COLOR),
            TEXT_RED_COLOR=os.getenv("TEXT_RED_COLOR", cls.TEXT_RED_COLOR),
            TEXT_DATETIME_FORMAT=os.getenv("TEXT_DATETIME_FORMAT", cls.TEXT_DATETIME_FORMAT),
            LOGS_PATH=Path(os.getenv("LOGS_PATH", str(cls.LOGS_PATH))),
            LOG_FILENAME=os.getenv("LOG_FILENAME"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", cls.LOG_LEVEL),
            LOG_MSG_FORMAT=os.getenv("LOG_MSG_FORMAT"),
            LOG_DATETIME_FORMAT=os.getenv("LOG_DATETIME_FORMAT"),
            SECRET_KEY=secret_key,
        )
