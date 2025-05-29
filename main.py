import os
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask, render_template, redirect, url_for, flash
from flask_caching import Cache

from libs.pi_info import PiInfo
from libs.log_utils import LoggerSingleton

load_dotenv('.env')

PORT = os.getenv("PORT", 8080)
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

pi_info = PiInfo(logger=logger)

config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 30,
    "SECRET_KEY": "pi_system'info"
}

app = Flask(__name__)
app.config.from_mapping(config)

cache = Cache(app)

app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

@app.route('/')
@cache.cached(timeout=INDEX_PAGE_CACHE_TIMEOUT)
def index(logger=logger):
    logger.info('Request index.html')
    return render_template("index.html", title=INDEX_PAGE_TITLE, index_url=url_for('index'))


@app.route('/restart')
def restart(logger=logger):
    flash("Rebooting... please wait.<br>This will take approx. one minute.", 'info')
    logger.info('Restart initiated from web interface')
    subprocess.Popen(["sudo", "reboot"])
    return render_template('system_action_pending.html',  title=INDEX_PAGE_TITLE, index_url=url_for('index'), action="Restart")


@app.route('/shutdown')
def shutdown(logger=logger):
    flash("Shutting down.<br>When the LEDs on the board stop flashing, it should be safe to unplug your Raspberry Pi.", 'info')
    logger.info('Shutdown initiated from web interface')
    subprocess.Popen(["sudo", "halt"])
    return render_template('system_action_pending.html',  title=INDEX_PAGE_TITLE,  index_url=url_for('index'), action="Shutdown")


@app.errorhandler(404)
def page_not_found_error(error):
    return render_template('error.html',  title=INDEX_PAGE_TITLE, error_code="404",
        error_message="Page not found", redirect_delay=5, index_url=url_for('index')), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html',  title=INDEX_PAGE_TITLE, error_code="500",
        error_message="Internal server error", redirect_delay=5, index_url=url_for('index')), 500


@app.context_processor
def pi_model_name(logger=logger):
    return dict(pi_model_name=pi_info.model_name)


@app.context_processor
def pi_revision(logger=logger):
    return dict(pi_revision=pi_info.revision)


@app.context_processor
def pi_serial_number(logger=logger):
    return dict(pi_serial_number=pi_info.serial_number)


@app.context_processor
def pi_manufacturer(logger=logger):
    return dict(pi_manufacturer=pi_info.manufacturer)


@app.context_processor
def pi_os(logger=logger):
    return dict(pi_os=pi_info.os_name)


@app.context_processor
def pi_hostname(logger=logger):
    return dict(pi_hostname=pi_info.hostname)


@app.context_processor
def uptime_since(logger=logger):
    return dict(uptime_since=pi_info.get_uptime_since().strftime(TEXT_DATETIME_FORMAT))


@app.context_processor
def uptime_pretty(logger=logger):
    return dict(uptime_pretty=pi_info.get_uptime_pretty())


@app.context_processor
def current_time(logger=logger):
    return dict(current_time=datetime.now().strftime(TEXT_DATETIME_FORMAT))


@app.context_processor
def cpu_model(logger=logger):
    return dict(cpu_model=pi_info.cpu_model)


@app.context_processor
def cpu_architecture(logger=logger):
    return dict(cpu_architecture=pi_info.cpu_architecture)


@app.context_processor
def cpu_cores_count(logger=logger):
    return dict(cpu_cores_count=pi_info.cpu_cores_count)


@app.context_processor
def cpu_core_frequency(logger=logger):
    return dict(cpu_core_frequency=pi_info.get_cpu_core_frequency())


@app.context_processor
def cpu_cache_sizes(logger=logger):
    return dict(cpu_cache_sizes=pi_info.cpu_cache_sizes)


@app.context_processor
def cpu_core_voltage(logger=logger):
    voltage = pi_info.get_cpu_core_voltage()
    return dict(cpu_core_voltage=f"{voltage: .3f}" if voltage is not None else None)


@app.context_processor
def cpu_usage(logger=logger):
    return dict(cpu_usage=pi_info.get_cpu_usage())


@app.context_processor
def cpu_temperature(logger=logger):
    temperature = pi_info.get_cpu_temperature()
    color = TEXT_GREEN_COLOR
    if temperature is not None:
        if CPU_ORANGE_TEMP_THRESHOLD < temperature < CPU_RED_TEMP_THRESHOLD:
            color = TEXT_ORANGE_COLOR
        elif temperature >= CPU_RED_TEMP_THRESHOLD:
            color = TEXT_RED_COLOR
    return dict(cpu_temperature={'temperature': temperature, 'color': color})


@app.context_processor
def memory_size(logger=logger):
    return dict(memory_size=pi_info.memory_size)


@app.context_processor
def ram_info(logger=logger):
    return dict(ram_info=pi_info.get_ram_info())


@app.context_processor
def ethernet_ip_info(logger=logger):
    ip_info = pi_info.get_ip_info('eth0')
    if ip_info is not None:
        default_str = 'Not connected'
        address = ip_info.get('ip', '')
        mask = ip_info.get('mask', '')
        return dict(
            ethernet_ip_address=address if len(address) > 0 else default_str,
            ethernet_network_mask=mask if len(mask) > 0 else default_str
        )
    else:
        return dict(ethernet_ip_address=None, ethernet_network_mask=None)


@app.context_processor
def ethernet_mac_address(logger=logger):
    address = pi_info.get_mac_address('eth0')
    return dict(ethernet_mac_address=address if address is not None and len(address) > 0 else 'Unknown')


@app.context_processor
def wifi_ip_address(logger=logger):
    ip_info = pi_info.get_ip_info('wlan0')
    if ip_info is not None:
        default_str = 'Not connected'
        address = ip_info.get('ip', '')
        mask = ip_info.get('mask', '')
        return dict(
            wifi_ip_address=address if len(address) > 0 else default_str,
            wifi_network_mask=mask if len(mask) > 0 else default_str
        )
    else:
        return dict(wifi_ip_address=None, wifi_network_mask=None)



@app.context_processor
def wifi_mac_address(logger=logger):
    address = pi_info.get_mac_address('wlan0')
    return dict(wifi_mac_address=address if address is not None and len(address) > 0 else 'Unknown')


@app.context_processor
def bluetooth_mac_address(logger=logger):
    address = pi_info.get_bluetooth_mac_address()
    return dict(bluetooth_mac_address=address if address is not None and len(address) > 0 else 'Unknown')


@app.context_processor
def available_wifi_networks(logger=logger):
    return dict(available_wifi_networks=pi_info.get_available_wifi_networks())


@app.context_processor
def disk_usage_info(logger=logger):
    return dict(disk_usage_info=pi_info.get_disk_usage_info())


@app.context_processor
def running_process_info(logger=logger):
    return dict(running_process_info=pi_info.get_running_process_info())


@app.context_processor
def utility_processor(logger=logger):
    def short_date(a,b,c):
        return u'{0}{1}, {2}'.format(a, b,c)
    return dict(short_date=short_date)


if __name__ == "__main__":
    logger.info("Started")
    try:
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("Stopped")
        exit()
