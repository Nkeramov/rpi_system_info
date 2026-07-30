import logging
import logging.handlers
from logging import Logger, LogRecord
from pathlib import Path
from typing import Any, ClassVar, TypedDict

from colorama import Fore, Style

from .cls_utils import Singleton


class CustomColoredFormatter(logging.Formatter):
    """
    Custom logging formatter that adds ANSI color codes to log levels.
    Uses the colorama library. Colors can be customized via the `colors` parameter.

    Class Attributes:
        LEVEL_COLORS (dict): Mapping of log level numbers to ANSI color codes.
    """
    LEVEL_COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: Fore.LIGHTBLUE_EX,
        logging.INFO: Fore.LIGHTGREEN_EX,
        logging.WARNING: Fore.LIGHTYELLOW_EX,
        logging.ERROR: Fore.LIGHTRED_EX,
        logging.CRITICAL: Fore.LIGHTRED_EX + Style.BRIGHT,
    }


    def __init__(
            self,
            fmt: str | None = None,
            datefmt: str | None = None,
            colors: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the colored formatter.

        Args:
            fmt (str | None): Log message format string.
            datefmt (str | None): Date/time format string.
            colors (dict[str, str] | None): Custom color mapping with keys
                'debug', 'info', 'warning', 'error', 'critical' and values as
                colorama color names (e.g., 'LIGHTRED_EX').
        """
        self.fmt = fmt
        self.datefmt = datefmt
        super().__init__(fmt=fmt, datefmt=datefmt)

        if colors:
            self.LEVEL_COLORS.update(
                {
                    getattr(logging, k.upper()): v
                    for k, v in colors.items()
                    if k.upper() in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
                },
            )

    def format(self, record: LogRecord) -> str:
        """
        Format the log record with color codes for the level.

        Args:
            record (LogRecord): The log record to format.

        Returns:
            str: The formatted log message with ANSI color codes.
        """
        log_fmt = self.fmt
        if record.levelno in self.LEVEL_COLORS:
            log_fmt = f"{self.LEVEL_COLORS[record.levelno]}{self.fmt}{Style.RESET_ALL}"
        formatter = logging.Formatter(fmt=log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


class LoggerConfig(TypedDict, total=False):
    log_dir: Path | str | None
    log_file: str | None
    level: str
    msg_format: str
    date_format: str
    colored: bool
    max_size_mb: int
    keep: int
    colors: dict[str, str] | None
    encoding: str
    file_msg_format: str | None
    file_date_format: str | None
    kwargs: dict[str, Any]


class LoggerSingleton(metaclass=Singleton):
    """
    Thread-safe singleton logger with console and rotating file output.

    The logger is configured upon first instantiation. Subsequent calls to the
    constructor return the same instance. If the class attribute
    `__allow_reinitialization` is set to True, re-initialization is permitted.

    Class Attributes:
        __logger (Logger): The internal logger instance.
        __allow_reinitialization (bool): Whether to allow re-initialization.
        DEFAULT_FORMAT (str): Default log message format.
        DEFAULT_DATE_FORMAT (str): Default date/time format.
    """
    __logger: Logger = logging.getLogger('SuperLogger')
    __allow_reinitialization: bool = False
    _initialized: bool = False
    _config: LoggerConfig = {}

    DEFAULT_FORMAT = '%(asctime)s | %(levelname)s | %(module)s | %(funcName)s | %(message)s'
    DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(
        self,
        log_dir: Path | str | None = None,
        log_file: str | None = None,
        level: str | None = None,
        msg_format: str | None = None,
        date_format: str | None = None,
        colored: bool = False,
        max_size_mb: int = 10,
        keep: int = 10,
        colors: dict[str, str] | None = None,
        encoding: str = "utf-8",
        file_msg_format: str | None = None,
        file_date_format: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize (or re-initialize) the logger.

        If an instance already exists and `__allow_reinitialization` is False,
        the constructor does nothing.

        Args:
            log_dir (Path | str | None): Directory for log files (if None, no file logging).
            log_file (str | None): Log file name.
            level (str | None): Logging level (e.g., 'INFO'). Defaults to 'INFO'.
            msg_format (str | None): Message format. Defaults to DEFAULT_FORMAT.
            date_format (str | None): Date format. Defaults to DEFAULT_DATE_FORMAT.
            colored (bool): Whether to enable colors in console output.
            max_size_mb (int): Maximum file size in MB before rotation.
            keep (int): Number of archived log files to keep.
            colors (dict[str, str] | None): Custom colors for the formatter.
            encoding (str): File encoding (default 'utf-8').
            file_msg_format (str | None): Separate format for file handler (uses msg_format if None).
            file_date_format (str | None): Separate date format for file handler (uses date_format if None).
            **kwargs: Additional arguments passed to the formatter.
        """
        if not type(self)._initialized or type(self).__allow_reinitialization:
            self._initialize_logger(
                log_dir=log_dir,
                log_file=log_file,
                level=level or "INFO",
                msg_format=msg_format or self.DEFAULT_FORMAT,
                date_format=date_format or self.DEFAULT_DATE_FORMAT,
                colored=colored,
                max_size_mb=max_size_mb,
                keep=keep,
                colors=colors,
                encoding=encoding,
                file_msg_format=file_msg_format,
                file_date_format=file_date_format,
                **kwargs,
            )
            type(self)._initialized = True

    def _initialize_logger(
        self,
        log_dir: Path | str | None,
        log_file: str | None,
        level: str,
        msg_format: str,
        date_format: str,
        colored: bool,
        max_size_mb: int,
        keep: int,
        colors: dict[str, str] | None = None,
        encoding: str = "utf-8",
        file_msg_format: str | None = None,
        file_date_format: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Configure the logger handlers. Clears any existing handlers.

        Args:
            log_dir (Path | str | None): Directory for log files (converted to Path if string).
            log_file (str | None): Log file name.
            level (str): Logging level.
            msg_format (str): Message format.
            date_format (str): Date format.
            colored (bool): Enable colors in console.
            max_size_mb (int): Max file size in MB.
            keep (int): Number of archives to keep.
            colors (dict[str, str] | None): Custom colors for formatter.
            encoding (str): File encoding.
            file_msg_format (str | None): Format for file handler (uses msg_format if None).
            file_date_format (str | None): Date format for file handler (uses date_format if None).
            **kwargs: Additional arguments for the formatter.
        """
        if log_dir is not None and not isinstance(log_dir, Path):
            log_dir = Path(log_dir)

        self.__class__.__logger.setLevel(level)
        self.__class__.__logger.handlers.clear()

        self._add_stream_handler(
            level=level,
            msg_format=msg_format,
            date_format=date_format,
            colored=colored,
            colors=colors,
            **kwargs,
        )

        if log_dir and log_file:
            self._add_file_handler(
                log_dir=log_dir,
                log_file=log_file,
                level=level,
                msg_format=file_msg_format or msg_format,
                date_format=file_date_format or date_format,
                max_size_mb=max_size_mb,
                keep=keep,
                encoding=encoding,
            )

        # Store current configuration for later updates
        self._config = {
            "log_dir": log_dir,
            "log_file": log_file,
            "level": level,
            "msg_format": msg_format,
            "date_format": date_format,
            "colored": colored,
            "max_size_mb": max_size_mb,
            "keep": keep,
            "colors": colors,
            "encoding": encoding,
            "file_msg_format": file_msg_format,
            "file_date_format": file_date_format,
            "kwargs": kwargs,
        }


    def _add_stream_handler(
        self,
        level: str,
        msg_format: str,
        date_format: str,
        colored: bool,
        colors: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a console (stdout) handler.

        Args:
            level (str): Logging level.
            msg_format (str): Message format.
            date_format (str): Date format.
            colored (bool): Enable colors.
            colors (dict[str, str] | None): Custom color mapping.
            **kwargs: Additional arguments for the formatter.
        """
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        formatter = (
            CustomColoredFormatter(fmt=msg_format, datefmt=date_format, colors=colors, **kwargs)
            if colored
            else logging.Formatter(fmt=msg_format, datefmt=date_format)
        )
        stream_handler.setFormatter(formatter)
        self.__class__.__logger.addHandler(stream_handler)

    def _add_file_handler(
        self,
        log_dir: Path,
        log_file: str,
        level: str,
        msg_format: str,
        date_format: str,
        max_size_mb: int,
        keep: int,
        encoding: str = "utf-8",
    ) -> None:
        """
        Add a rotating file handler.

        Args:
            log_dir (Path): Directory for the log file (created if it does not exist).
            log_file (str): Log file name.
            level (str): Logging level.
            msg_format (str): Message format.
            date_format (str): Date format.
            max_size_mb (int): Maximum file size in MB.
            keep (int): Number of archived files to keep.
            encoding (str): File encoding (default 'utf-8').

        Raises:
            OSError: If the directory cannot be created or the file cannot be opened.
        """
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_path = log_dir / log_file

            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=keep,
                encoding=encoding,
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(
                logging.Formatter(fmt=msg_format, datefmt=date_format),
            )
            self.__class__.__logger.addHandler(file_handler)
        except OSError as e:
            self.__logger.error(f"Failed to initialize file handler: {e}", exc_info=True)
            raise

    @classmethod
    def get_logger(cls) -> Logger:
        """
        Return the configured logger instance.

        If the instance has not been created or initialized, it is created with
        default parameters.

        Returns:
            Logger: The internal logger object.

        Raises:
            RuntimeError: If the logger is not a valid Logger instance.
        """
        if not cls._initialized:
            cls()
        if not isinstance(cls.__logger, Logger):
            raise RuntimeError("Logger was not properly initialized")
        return cls.__logger

    @classmethod
    def update_config(
        cls,
        log_dir: Path | str | None = None,
        log_file: str | None = None,
        level: str | None = None,
        msg_format: str | None = None,
        date_format: str | None = None,
        colored: bool | None = None,
        max_size_mb: int | None = None,
        keep: int | None = None,
        colors: dict[str, str] | None = None,
        encoding: str | None = None,
        file_msg_format: str | None = None,
        file_date_format: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Update the logger configuration.

        Clears all existing handlers and adds new ones with the updated parameters.
        Parameters not explicitly provided retain their current values.
        If the instance has not been created yet, it is created with the provided
        parameters.

        Args:
            log_dir (Path | str | None): Directory for log files (if None, file logging is disabled).
            log_file (str | None): Log file name.
            level (str | None): Logging level.
            msg_format (str | None): Message format.
            date_format (str | None): Date format.
            colored (bool | None): Enable colors.
            max_size_mb (int | None): Max file size in MB.
            keep (int | None): Number of archives to keep.
            colors (dict[str, str] | None): Custom color mapping.
            encoding (str | None): File encoding.
            file_msg_format (str | None): Separate format for file handler.
            file_date_format (str | None): Separate date format for file handler.
            **kwargs: Additional arguments for the formatter.

        Note:
            This method is thread-safe due to the singleton lock.
        """
        if not cls._initialized:
            cls()

        config = cls()._config
        new_config: LoggerConfig = {
            "log_dir": log_dir if log_dir is not None else config.get("log_dir"),
            "log_file": log_file if log_file is not None else config.get("log_file"),
            "level": level if level is not None else config.get("level", "INFO"),
            "msg_format": msg_format if msg_format is not None else config.get("msg_format", cls.DEFAULT_FORMAT),
            "date_format": date_format if date_format is not None else config.get("date_format", cls.DEFAULT_DATE_FORMAT),
            "colored": colored if colored is not None else config.get("colored", False),
            "max_size_mb": max_size_mb if max_size_mb is not None else config.get("max_size_mb", 10),
            "keep": keep if keep is not None else config.get("keep", 10),
            "colors": colors if colors is not None else config.get("colors"),
            "encoding": encoding if encoding is not None else config.get("encoding", "utf-8"),
            "file_msg_format": file_msg_format if file_msg_format is not None else config.get("file_msg_format"),
            "file_date_format": file_date_format if file_date_format is not None else config.get("file_date_format"),
            "kwargs": kwargs if kwargs else config.get("kwargs", {}),
        }

        # Re-initialize with the merged configuration
        with Singleton._lock:
            cls()._initialize_logger(**new_config)

    @classmethod
    def set_level(cls, level: str) -> None:
        """
        Change the logging level for the logger and all its handlers.

        Args:
            level (str): The new logging level (e.g., 'DEBUG').
        """
        logger = cls.get_logger()
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
