from logging import Logger
from flask import Flask, render_template, url_for
from werkzeug.exceptions import NotFound, InternalServerError

from ..config import AppConfig


def register(app: Flask, logger: Logger, config: AppConfig) -> None:
    @app.errorhandler(404)
    def page_not_found_error(error: NotFound) -> tuple[str, int]:
        logger.error(f"404 error: {error}")
        return render_template('error.html', title=config.PAGE_TITLE, error_code="404",
                               error_message="Page not found", redirect_delay=5, index_url=url_for('index')), 404

    @app.errorhandler(500)
    def internal_server_error(error: InternalServerError) -> tuple[str, int]:
        logger.error(f"500 error: {error}")
        return render_template('error.html', title=config.PAGE_TITLE, error_code="500",
                               error_message="Internal server error", redirect_delay=5, index_url=url_for('index')), 500
