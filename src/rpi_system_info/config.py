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

    METRICS_UPDATE_INTERVAL: int = 30
    METRICS_TTL: int = 60

    USAGE_NORMAL_COLOR: str ="#00FF40"
    USAGE_WARNING_COLOR: str ="#FF8C00"
    USAGE_CRITICAL_COLOR: str ="#CC0000"

    TEMP_NORMAL_COLOR: str ="#00FF40"
    TEMP_WARNING_COLOR: str ="#FF8C00"
    TEMP_CRITICAL_COLOR: str ="#CC0000"

    USAGE_WARNING_THRESHOLD: float = 65.0
    USAGE_CRITICAL_THRESHOLD: float = 85.0

    TEMP_WARNING_THRESHOLD: float = 55.0
    TEMP_CRITICAL_THRESHOLD: float = 65.0

    TEXT_DATETIME_FORMAT: str = "%d-%b-%Y, %H:%M:%S"

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
            METRICS_UPDATE_INTERVAL=int(os.getenv("METRICS_UPDATE_INTERVAL", cls.METRICS_UPDATE_INTERVAL)),
            METRICS_TTL=int(os.getenv("METRICS_TTL", cls.METRICS_TTL)),
            USAGE_NORMAL_COLOR=os.getenv("USAGE_NORMAL_COLOR", cls.USAGE_NORMAL_COLOR),
            USAGE_WARNING_COLOR=os.getenv("USAGE_WARNING_COLOR", cls.USAGE_WARNING_COLOR),
            USAGE_CRITICAL_COLOR=os.getenv("USAGE_CRITICAL_COLOR", cls.USAGE_CRITICAL_COLOR),
            TEMP_NORMAL_COLOR=os.getenv("TEMP_NORMAL_COLOR", cls.TEMP_NORMAL_COLOR),
            TEMP_WARNING_COLOR=os.getenv("TEMP_WARNING_COLOR", cls.TEMP_WARNING_COLOR),
            TEMP_CRITICAL_COLOR=os.getenv("TEMP_CRITICAL_COLOR", cls.TEMP_CRITICAL_COLOR),
            USAGE_WARNING_THRESHOLD=float(os.getenv("USAGE_WARNING_THRESHOLD", cls.USAGE_WARNING_THRESHOLD)),
            USAGE_CRITICAL_THRESHOLD=float(os.getenv("USAGE_CRITICAL_THRESHOLD", cls.USAGE_CRITICAL_THRESHOLD)),
            TEMP_WARNING_THRESHOLD=float(os.getenv("TEMP_WARNING_THRESHOLD", cls.TEMP_WARNING_THRESHOLD)),
            TEMP_CRITICAL_THRESHOLD=float(os.getenv("TEMP_CRITICAL_THRESHOLD", cls.TEMP_CRITICAL_THRESHOLD)),
            TEXT_DATETIME_FORMAT=os.getenv("TEXT_DATETIME_FORMAT", cls.TEXT_DATETIME_FORMAT),
            LOGS_PATH=Path(os.getenv("LOGS_PATH", str(cls.LOGS_PATH))),
            LOG_FILENAME=os.getenv("LOG_FILENAME"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", cls.LOG_LEVEL),
            LOG_MSG_FORMAT=os.getenv("LOG_MSG_FORMAT"),
            LOG_DATETIME_FORMAT=os.getenv("LOG_DATETIME_FORMAT"),
            SECRET_KEY=secret_key,
        )
