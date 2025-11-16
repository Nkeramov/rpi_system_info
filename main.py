import os
import time
import secrets
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask, Response, render_template, url_for, flash, after_this_request
from flask_caching import Cache

from werkzeug.exceptions import NotFound, InternalServerError

from logging import Logger

from libs.rpi_system_info import RPiSystemInfo
from libs.log_utils import LoggerSingleton

from typing import Any

load_dotenv('.env')

PORT = int(os.getenv("PORT", 8080))
INDEX_PAGE_CACHE_TIMEOUT = int(os.getenv("INDEX_PAGE_CACHE_TIMEOUT", 10))
INDEX_PAGE_TITLE = os.getenv("INDEX_PAGE_TITLE", 'Raspberry Pi System Info')

CPU_ORANGE_TEMP_THRESHOLD = float(os.getenv("CPU_ORANGE_TEMP_THRESHOLD", 50))
CPU_RED_TEMP_THRESHOLD = float(os.getenv("CPU_RED_TEMP_THRESHOLD", 60))

TEXT_GREEN_COLOR = os.getenv("TEXT_GREEN_COLOR", "#00FF40")
TEXT_ORANGE_COLOR = os.getenv("TEXT_ORANGE_COLOR", "#FF8C00")
TEXT_RED_COLOR = os.getenv("TEXT_RED_COLOR", "#CC0000")

TEXT_DATETIME_FORMAT = os.getenv("TEXT_DATETIME_FORMAT", "%d-%b-%Y, %H : %M : %S")

logger = LoggerSingleton(
    log_dir=Path(os.getenv("LOGS_PATH", "logs")),
    log_file=os.getenv("LOG_FILENAME"),
    level=os.getenv("LOG_LEVEL"),
    msg_format=os.getenv("LOG_MSG_FORMAT"),
    date_format=os.getenv("LOG_DATETIME_FORMAT"),
    colored=True
).get_logger()

rpi_info = RPiSystemInfo(logger=logger)

config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 30,
    "SECRET_KEY": secrets.token_hex(32)
}
app = Flask(__name__)
app.config.from_mapping(config)

cache = Cache(app)

app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)


@app.route('/')
@cache.cached(timeout=INDEX_PAGE_CACHE_TIMEOUT)
def index(logger: Logger = logger) -> str:
    logger.info('Request index.html')
    return render_template('index.html', title=INDEX_PAGE_TITLE, index_url=url_for('index'))


@app.route('/reboot')
def restart(logger: Logger = logger) -> str:
    logger.info('Reboot initiated from web interface')
    messages = [
        'Rebooting... please wait.',
        'This will take approx. one minute.',
        'This page will not automatically refresh. You will need to manually reconnect to the system after a restart.'
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

    return render_template('system_action_pending.html', title=INDEX_PAGE_TITLE, index_url=url_for('index'))


@app.route('/shutdown')
def shutdown(logger: Logger = logger) -> str:
    logger.info('Shutdown initiated from web interface')
    messages = [
	    'Shutting down.',
        'When the LEDs on the board stop flashing, it should be safe to unplug your Raspberry Pi.',
        'This page will not automatically refresh. You will need to manually reconnect to the system after a restart.'
    ]
    for message in messages:
        flash(message, 'info')

    @after_this_request
    def delayed_restart(response: Response) -> Response:
        def restart_thread() -> None:
            time.sleep(3)
            subprocess.Popen(["sudo", "halt"])

        threading.Thread(target=restart_thread).start()
        return response

    return render_template('system_action_pending.html', title=INDEX_PAGE_TITLE, index_url=url_for('index'))


@app.errorhandler(404)
def page_not_found_error(error: NotFound) -> tuple[str, int]:
    return render_template('error.html',  title=INDEX_PAGE_TITLE, error_code="404",
        error_message="Page not found", redirect_delay=5, index_url=url_for('index')), 404


@app.errorhandler(500)
def internal_server_error(error: InternalServerError) -> tuple[str, int]:
    return render_template('error.html',  title=INDEX_PAGE_TITLE, error_code="500",
        error_message="Internal server error", redirect_delay=5, index_url=url_for('index')), 500


@app.context_processor
def generic_board_info(logger: Logger = logger) -> dict[str, dict[str, Any]]:
    system_time = datetime.now().strftime(TEXT_DATETIME_FORMAT)
    boot_time = rpi_info.boot_time
    boot_time_str = boot_time.strftime(TEXT_DATETIME_FORMAT) if boot_time else ''
    return dict(generic_board_info=
        {
            'model_name': rpi_info.model_name,
            'revision': rpi_info.revision,
            'serial_number': rpi_info.serial_number,
            'manufacturer': rpi_info.manufacturer,
            'os': rpi_info.os_name,
            'hostname': rpi_info.hostname,
            'system_time': system_time,
            'boot_time': boot_time_str,
            'uptime_pretty': rpi_info.get_uptime_pretty(),
            'internet_connection_status': rpi_info.check_internet_connection(),
            'public_ip': rpi_info.get_public_ip()
        }
    )


@app.context_processor
def cpu_details(logger: Logger = logger) -> dict[str, dict[str, Any]]:
    temperature = rpi_info.get_cpu_temperature()
    color = TEXT_GREEN_COLOR
    if temperature is not None:
        if CPU_ORANGE_TEMP_THRESHOLD < temperature < CPU_RED_TEMP_THRESHOLD:
            color = TEXT_ORANGE_COLOR
        elif temperature >= CPU_RED_TEMP_THRESHOLD:
            color = TEXT_RED_COLOR
    voltage = rpi_info.get_cpu_core_voltage()
    return dict(cpu_details=
        {
            'model': rpi_info.cpu_model,
            'architecture': rpi_info.cpu_architecture,
            'cores_count': rpi_info.cpu_cores_count,
            'min_core_frequency': rpi_info.get_cpu_core_frequencies()['min'],
            'cur_core_frequency': rpi_info.get_cpu_core_frequencies()['cur'],
            'max_core_frequency': rpi_info.get_cpu_core_frequencies()['max'],
            'core_voltage': f"{voltage: .3f}" if voltage is not None else None,
            'cache_sizes': rpi_info.cpu_cache_sizes,
            'usage': rpi_info.get_cpu_usage(),
            'temperature_value': temperature,
            'temperature_color': color,
            'overvoltage_allowed': 'Yes' if rpi_info.overvoltage_allowed else 'No',
            'otp_programming_allowed': 'Yes' if rpi_info.otp_programming_allowed else 'No',
            'otp_reading_allowed': 'Yes' if rpi_info.otp_reading_allowed else 'No'
        }
    )


@app.context_processor
def ram_details(logger: Logger = logger) -> dict[str, dict[str, str]]:
    return dict(ram_details=rpi_info.get_ram_info())


@app.context_processor
def eth_interface_info(logger: Logger = logger) -> dict[str, dict[str, str]]:
    return dict(eth_info=rpi_info.get_network_interface_info('eth0'))


@app.context_processor
def wlan_interface_info(logger: Logger = logger) -> dict[str, dict[str, str]]:
    return dict(wlan_info=rpi_info.get_network_interface_info('wlan0'))


@app.context_processor
def wifi_network_name(logger: Logger = logger) -> dict[str, str]:
    network_name = rpi_info.get_wifi_network_name()
    return dict(wifi_network_name=network_name)


@app.context_processor
def bluetooth_mac_address(logger: Logger = logger) -> dict[str, str]:
    address = rpi_info.get_bluetooth_mac_address()
    return dict(bluetooth_mac_address=address)


@app.context_processor
def available_wifi_networks(logger: Logger = logger) -> dict[str, list[dict[str, str]]]:
    return dict(available_wifi_networks=rpi_info.get_available_wifi_networks())


@app.context_processor
def disks_details(logger: Logger = logger) -> dict[str, list[dict[str, str]]]:
    return dict(disks_details=rpi_info.get_disks_info())


@app.context_processor
def disks_inodes_details(logger: Logger = logger) -> dict[str, list[dict[str, str]]]:
    return dict(disks_inodes_details=rpi_info.get_disks_inodes_info())


@app.context_processor
def processes_details(logger: Logger = logger) -> dict[str, list[dict[str, Any]]]:
    processes_details = rpi_info.get_processes_info()
    for process in processes_details:
        process['started_on'] = process['started_on'].strftime(TEXT_DATETIME_FORMAT)
    return dict(processes_details=processes_details)


if __name__ == "__main__":
    logger.info("Started")
    try:
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("Stopped")
        exit()
