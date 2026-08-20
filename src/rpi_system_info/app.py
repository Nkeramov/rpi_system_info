from flask import Flask
from flask_caching import Cache

from .config import AppConfig
from .core.cache_manager import CacheManager
from .core.system_info import RPiSystemInfo
from .core.utils.log_utils import LoggerSingleton
from .web import error_handlers, routes


def create_app(config: AppConfig | None = None) -> Flask:
    if config is None:
        config = AppConfig.from_env()

    logger = LoggerSingleton(
        log_dir=config.LOGS_PATH,
        log_file=config.LOG_FILENAME,
        level=config.LOG_LEVEL,
        msg_format=config.LOG_MSG_FORMAT,
        date_format=config.LOG_DATETIME_FORMAT,
        colored=True,
    ).get_logger()
    logger.info("Logger initialized")

    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config.from_mapping(DEBUG=False)

    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)

    page_cache = Cache(app, config={
            "CACHE_TYPE": "SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": config.PAGE_CACHE_TIMEOUT,
        },
    )

    rpi_info = RPiSystemInfo(logger)

    metrics_cache_manager = CacheManager(rpi_info, config, logger)

    routes.register(app, config, page_cache, metrics_cache_manager, rpi_info, logger)
    error_handlers.register(app, logger, config)

    return app
