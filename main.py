import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask, render_template
from flask_caching import Cache

from libs.pi_system_info import PiSystemInfo
from libs.log_utils import LoggerSingleton

load_dotenv('.env')

PORT = os.getenv("PORT", 8080)
INDEX_PAGE_CACHE_TIMEOUT = int(os.getenv("INDEX_PAGE_CACHE_TIMEOUT", 10))

CPU_ORANGE_TEMP_THRESHOLD = float(os.getenv("CPU_ORANGE_TEMP_THRESHOLD", 50))
CPU_RED_TEMP_THRESHOLD = float(os.getenv("CPU_RED_TEMP_THRESHOLD", 60))

TEXT_GREEN_COLOR = os.getenv("TEXT_GREEN_COLOR", "#00FF40")
TEXT_ORANGE_COLOR = os.getenv("TEXT_ORANGE_COLOR", "#FF8C00")
TEXT_RED_COLOR = os.getenv("TEXT_RED_COLOR", "#CC0000")

TEXT_DATETIME_FORMAT = os.getenv("TEXT_DATETIME_FORMAT", "%d-%b-%Y, %H : %M : %S")

logger = LoggerSingleton(
    log_dir=Path(os.getenv("LOGS_PATH", "logs")),
    log_file='pi_system_info_server.log',
    level=os.getenv("LOG_LEVEL"),
    msg_format=os.getenv("LOG_MSG_FORMAT"),
    date_format=os.getenv("LOG_DATETIME_FORMAT"),
    colored=True
).get_logger()

pi_sys_info = PiSystemInfo(logger=logger)

config = {
    'CACHE_TYPE': 'SimpleCache',
    "CACHE_DEFAULT_TIMEOUT": 300
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
    return render_template("index.html", title='Raspberry Pi System Info')


@app.route('/restart')
def restart(logger=logger):
    logger.info('Restart')
    os.system('sudo reboot now')


@app.route('/shutdown')
def shutdown(logger=logger):
    logger.info('Shutdown')
    os.system('sudo stutdown now')


@app.context_processor
def pi_hostname(logger=logger):
    return dict(pi_hostname=pi_sys_info.get_hostname())


@app.context_processor
def pi_model(logger=logger):
    return dict(pi_model=pi_sys_info.get_model())


@app.context_processor
def pi_os(logger=logger):
    return dict(pi_os=pi_sys_info.get_os_name())


@app.context_processor
def uptime_since(logger=logger):
    return dict(uptime_since=pi_sys_info.get_uptime_since().strftime(TEXT_DATETIME_FORMAT))


@app.context_processor
def uptime_pretty(logger=logger):
    return dict(uptime_pretty=pi_sys_info.get_uptime_pretty())


@app.context_processor
def current_time(logger=logger):
    return dict(current_time=datetime.now().strftime(TEXT_DATETIME_FORMAT))


@app.context_processor
def cpu_architecture(logger=logger):
    return dict(cpu_architecture=pi_sys_info.get_cpu_architecture())


@app.context_processor
def cpu_model_name(logger=logger):
    return dict(cpu_model_name=pi_sys_info.get_cpu_model_name())


@app.context_processor
def cpu_hardware_type(logger=logger):
    return dict(cpu_hardware_type=pi_sys_info.get_cpu_hardware_type())


@app.context_processor
def cpu_serial_number(logger=logger):
    return dict(cpu_serial_number=pi_sys_info.get_cpu_serial_number())


@app.context_processor
def cpu_revision(logger=logger):
    return dict(cpu_revision=pi_sys_info.get_cpu_revision())


@app.context_processor
def cpu_core_frequency(logger=logger):
    return dict(cpu_core_frequency=pi_sys_info.get_cpu_core_frequency())


@app.context_processor
def cpu_core_count(logger=logger):
    return dict(cpu_core_count=pi_sys_info.get_cpu_core_count())


@app.context_processor
def cpu_core_voltage(logger=logger):
    return dict(cpu_core_voltage=f"{pi_sys_info.get_cpu_core_voltage(): .3f}")


@app.context_processor
def cpu_usage(logger=logger):
    return dict(cpu_usage=pi_sys_info.get_cpu_usage())


@app.context_processor
def cpu_temperature(logger=logger):
    temperature = pi_sys_info.get_cpu_temperature()
    color = TEXT_GREEN_COLOR
    if CPU_ORANGE_TEMP_THRESHOLD < temperature < CPU_RED_TEMP_THRESHOLD:
        color = TEXT_ORANGE_COLOR
    elif temperature >= CPU_RED_TEMP_THRESHOLD:
        color = TEXT_RED_COLOR
    return dict(cpu_temperature={'temperature': temperature, 'color': color})


@app.context_processor
def cpu_cache_sizes(logger=logger):
    return dict(cpu_cache_sizes=pi_sys_info.get_cpu_cache_sizes())


@app.context_processor
def ram_info(logger=logger):
    return dict(ram_info=pi_sys_info.get_ram_info())


@app.context_processor
def ethernet_ip_address(logger=logger):
    address = pi_sys_info.get_ip_address('eth0')
    return dict(ethernet_ip_address=address if address is not None and len(address) > 0 else 'Not connected')


@app.context_processor
def ethernet_mac_address(logger=logger):
    address = pi_sys_info.get_mac_address('eth0')
    return dict(ethernet_mac_address=address if address is not None and len(address) > 0 else 'Unknown')

@app.context_processor
def wifi_ip_address(logger=logger):
    address = pi_sys_info.get_ip_address('wlan0')
    return dict(wifi_ip_address=address if address is not None and len(address) > 0 else 'Not connected')


@app.context_processor
def wifi_mac_address(logger=logger):
    address = pi_sys_info.get_mac_address('wlan0')
    return dict(wifi_mac_address=address if address is not None and len(address) > 0 else 'Unknown')


@app.context_processor
def bluetooth_mac_address(logger=logger):
    address = pi_sys_info.get_bluetooth_mac_address()
    return dict(bluetooth_mac_address=address if address is not None and len(address) > 0 else 'Unknown')


@app.context_processor
def available_wifi_networks(logger=logger):
    return dict(available_wifi_networks=pi_sys_info.get_available_wifi_networks())


@app.context_processor
def disk_usage_info(logger=logger):
    return dict(disk_usage_info=pi_sys_info.get_disk_usage_info())


@app.context_processor
def running_process_info(logger=logger):
    return dict(running_process_info=pi_sys_info.get_running_process_info())


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
