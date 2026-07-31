from flask import Flask
from flask_caching import Cache

from .config import AppConfig
from .core.utils.log_utils import LoggerSingleton
from .core.system_info import RPiSystemInfo
from .web import routes, error_handlers


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

    cache = Cache(app, config={
            "CACHE_TYPE": "SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": config.INDEX_PAGE_CACHE_TIMEOUT
        }
    )

    rpi_info = RPiSystemInfo(logger=logger)

    routes.register(app, rpi_info, cache, logger, config)
    error_handlers.register(app, logger, config)

    return app
