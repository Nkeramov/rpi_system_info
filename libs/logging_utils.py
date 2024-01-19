import logging
from logging import Logger


def get_logger(level: str, msg_format: str, date_format: str, filename: str | None = None, filemode='a') -> Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.getLevelName(level))

    stream = logging.StreamHandler()
    stream.setLevel(logging.getLevelName(level))
    stream_format = logging.Formatter(fmt=msg_format, datefmt=date_format)
    stream.setFormatter(stream_format)
    logger.addHandler(stream)
    if filename:
        file = logging.FileHandler(filename, mode=filemode, encoding="utf-8")
        file.setLevel(logging.getLevelName(level))
        file_format = logging.Formatter(fmt=msg_format, datefmt=date_format)
        file.setFormatter(file_format)
        logger.addHandler(file)
    return logger
