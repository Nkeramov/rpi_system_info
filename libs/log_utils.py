import logging
import logging.handlers
from pathlib import Path
from logging import Logger
from typing import Optional

from .cls_utils import Singleton


class CustomColoredFormatter(logging.Formatter):
    """Custom logging colored formatter"""

    green = "\x1b[38;5;40m"
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = "\x1b[0m"
    default_fmt: str = '%(asctime)s | %(levelname)s | %(module)s | %(funcName)s | %(lineno)s | %(message)s'
    default_datefmt: str = '%Y-%m-%d %H:%M:%S'


    def __init__(self, fmt: str = None, datefmt: str = None):
        fmt = fmt or self.default_fmt
        datefmt = datefmt or self.default_datefmt
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.FORMATS = {
            logging.DEBUG: self.green + self._fmt + self.reset,
            logging.INFO: self.green + self._fmt + self.reset,
            logging.WARNING: self.yellow + self._fmt + self.reset,
            logging.ERROR: self.red + self._fmt + self.reset,
            logging.CRITICAL: self.bold_red + self._fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(fmt=log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


class LoggerSingleton(metaclass=Singleton):
    __allow_reinitialization: bool = False
    __logger: Logger = None

    def __init__(self,
                 log_dir: Optional[Path] = None, log_file: str = None, level: str = 'INFO',
                 msg_format: str = '%(asctime)s | %(levelname)s | %(module)s | %(funcName)s | %(lineno)s | %(message)s',
                 date_format: str = '%Y-%m-%d %H:%M:%S',
                 colored: bool = False, max_size_mb=10, keep=10):
        LoggerSingleton.__logger = logging.getLogger('SuperLogger')
        LoggerSingleton.__logger.setLevel(logging.getLevelName(level))
        LoggerSingleton.__logger.handlers.clear()
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.getLevelName(level))
        stream_formatter = CustomColoredFormatter(fmt=msg_format, datefmt=date_format) if colored \
            else logging.Formatter(fmt=msg_format, datefmt=date_format)
        stream_handler.setFormatter(stream_formatter)
        LoggerSingleton.__logger.addHandler(stream_handler)
        if log_dir and not Path(log_dir).exists():
            try:
                Path(log_dir).mkdir()
            except Exception as e:
                print(e, 'Could not create log dir. Critical error, terminating...')
                exit()

        file_path = Path(log_dir, log_file) if log_dir and log_file else None

        if file_path:
            file_handler = logging.handlers.RotatingFileHandler(file_path, maxBytes=max_size_mb * 1048576,
                                                                backupCount=keep, encoding="utf-8")
            file_handler.setLevel(logging.getLevelName(level))
            file_formatter = logging.Formatter(fmt=msg_format, datefmt=date_format)
            file_handler.setFormatter(file_formatter)
            LoggerSingleton.__logger.addHandler(file_handler)

    @classmethod
    def get_logger(cls) -> Logger:
        if not cls.__logger:
            cls()
        return cls.__logger
