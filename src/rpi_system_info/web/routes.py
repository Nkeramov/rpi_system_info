import subprocess
import threading
import time

from flask import after_this_request, flash, render_template, url_for, Response


def register(app, rpi_info, cache, logger, config):
    @app.route('/')
    @cache.cached(timeout=config.INDEX_PAGE_CACHE_TIMEOUT)
    def index():
        logger.info('Request index.html')
        return render_template('index.html', title=config.INDEX_PAGE_TITLE, index_url=url_for('index'))

    @app.route('/reboot')
    def restart():
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

        return render_template('system_action_pending.html', title=config.INDEX_PAGE_TITLE, index_url=url_for('index'))

    @app.route('/shutdown')
    def shutdown():
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

        return render_template('system_action_pending.html', title=config.INDEX_PAGE_TITLE, index_url=url_for('index'))
