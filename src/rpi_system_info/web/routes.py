import subprocess
import threading
import time
from typing import Any

from ..core.data_providers import (
    get_generic_data,
    get_hardware_data,
    get_network_data,
    get_storage_data,
    get_processes_data,
)

from flask import Flask, abort, after_this_request, flash, render_template, url_for, Response
from flask_caching import Cache
from logging import Logger

from ..config import AppConfig
from ..core.system_info import RPiSystemInfo
from ..core.utils.helpers import format_datetime


def register(app: Flask, rpi_info: RPiSystemInfo, cache: Cache, logger: Logger, config: AppConfig) -> None:
    @app.route('/')
    @cache.cached(timeout=config.PAGE_CACHE_TIMEOUT)
    def index() -> str:
        logger.info('Requested index page')
        return render_template('index.html', title=config.PAGE_TITLE, index_url=url_for('index'))


    @app.route('/partial/<section>')
    @cache.cached(timeout=config.PAGE_CACHE_TIMEOUT)
    def partial_section(section: str) -> str:
        logger.info(f'Requested {section} tab')
        data: dict[str, Any]
        if section == 'generic':
            data = get_generic_data(rpi_info, config)
            return render_template('partials/generic.html', **data)
        elif section == 'hardware':
            data = get_hardware_data(rpi_info, config)
            return render_template('partials/hardware.html', **data)
        elif section == 'networks':
            data = get_network_data(rpi_info)
            return render_template('partials/networks.html', **data)
        elif section == 'storage':
            data = get_storage_data(rpi_info)
            return render_template('partials/storage.html', **data)
        elif section == 'processes':
            data = get_processes_data(rpi_info, config)
            return render_template('partials/processes.html', **data)
        else:
            abort(404)

    @app.route('/reboot')
    def restart() -> str:
        logger.info('Reboot initiated from web interface')
        messages = [
            'Rebooting... please wait.',
            'This will take approx. one minute.',
            'This page will not automatically refresh. You will need to manually reconnect to the system after a restart.',
        ]
        for message in messages:
            flash(message, 'info')

        @after_this_request
        def delayed_restart(response: Response) -> Response:
            def restart_thread() -> None:
                time.sleep(3)
                subprocess.Popen(["sudo", "reboot"])

            threading.Thread(target=restart_thread).start()
            return response

        return render_template('system_action_pending.html', title=config.PAGE_TITLE, index_url=url_for('index'))

    @app.route('/shutdown')
    def shutdown() -> str:
        logger.info('Shutdown initiated from web interface')
        messages = [
            'Shutting down.',
            'When the LEDs on the board stop flashing, it should be safe to unplug your Raspberry Pi.',
            'This page will not automatically refresh. You will need to manually reconnect to the system after a restart.',
        ]
        for message in messages:
            flash(message, 'info')

        @after_this_request
        def delayed_shutdown(response: Response) -> Response:
            def shutdown_thread() -> None:
                time.sleep(3)
                subprocess.Popen(["sudo", "halt"])

            threading.Thread(target=shutdown_thread).start()
            return response

        return render_template('system_action_pending.html', title=config.PAGE_TITLE, index_url=url_for('index'))

