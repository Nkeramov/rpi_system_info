import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from libs.logging_utils import get_logger

load_dotenv('.env')

LOGS_PATH = os.getenv("LOGS_PATH")
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_MSG_FORMAT = os.getenv("LOG_MSG_FORMAT")
LOG_DATE_FORMAT = os.getenv("LOG_DATE_FORMAT")
LOG_FILENAME = os.path.join(LOGS_PATH, os.getenv("LOG_FILENAME"))
logger = get_logger(LOG_LEVEL, LOG_MSG_FORMAT, LOG_DATE_FORMAT, LOG_FILENAME)


from libs.pi_system_info import PiSystemInfo

pi_sys_info = PiSystemInfo(logger)

from flask import Flask, render_template
from flask_caching import Cache

config={
    'CACHE_TYPE': 'SimpleCache',
    "CACHE_DEFAULT_TIMEOUT": 300
}

app = Flask(__name__)

app.config.from_mapping(config)

cache = Cache(app)

app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)


@app.route('/')
# cached for 60 seconds
@cache.cached(timeout=60)
def index():
    app.logger.info('Request index.html')
    return render_template("index.html", title='Raspberry Pi System Info')


@app.route('/restart')
def restart():
    app.logger.info('Restart')
    os.system('sudo reboot now')


@app.route('/shutdown')
def shutdown():
    app.logger.info('Shutdown')
    os.system('sudo stutdown now')


@app.context_processor
def uptime_since():
    t = datetime.strptime(pi_sys_info.get_uptime_since(), "%Y-%m-%d %H:%M:%S")
    return dict(uptime_since=t.strftime("%d-%b-%Y, %I : %M : %S"))


@app.context_processor
def uptime_pretty():
    return dict(uptime_pretty=pi_sys_info.get_uptime_pretty())


@app.context_processor
def current_time():
    return dict(current_time=datetime.now().strftime("%d-%b-%Y, %I : %M : %S"))


@app.context_processor
def ip_address():
    return dict(ip_address=pi_sys_info.get_ip_address())


@app.context_processor
def mac_address():
    return dict(mac_address=pi_sys_info.get_mac_address().upper())


@app.context_processor
def cpu_model_name():
    return dict(cpu_model_name=pi_sys_info.get_cpu_model_name())


@app.context_processor
def cpu_hardware_type():
    return dict(cpu_hardware_type=pi_sys_info.get_cpu_hardware_type())


@app.context_processor
def cpu_serial_number():
    return dict(cpu_serial_number=pi_sys_info.get_cpu_serial_number())


@app.context_processor
def cpu_revision():
    return dict(cpu_revision=pi_sys_info.get_cpu_revision())


@app.context_processor
def cpu_core_frequency():
    return dict(cpu_core_frequency=pi_sys_info.get_cpu_core_frequency())


@app.context_processor
def cpu_core_count():
    return dict(cpu_core_count=pi_sys_info.get_cpu_core_count())


@app.context_processor
def cpu_core_voltage():
    return dict(cpu_core_voltage=f"{pi_sys_info.get_cpu_core_voltage(): .3f}")


@app.context_processor
def cpu_usage():
    return dict(cpu_usage=pi_sys_info.get_cpu_usage())


@app.context_processor
def cpu_temperature():
    temperature = pi_sys_info.get_cpu_temperature()
    color = 'white'
    if 40 < temperature < 50:
        color = 'orange'
    elif temperature >= 50:
        color = 'red'
    return dict(cpu_temperature={'temperature': temperature, 'color': color})


@app.context_processor
def pi_hostname():
    return dict(pi_hostname=pi_sys_info.get_hostname())


@app.context_processor
def ram_info():
    return dict(ram_info=pi_sys_info.get_ram_info())


@app.context_processor
def pi_model():
    return dict(pi_model=pi_sys_info.get_model())


@app.context_processor
def pi_os():
    return dict(pi_os=pi_sys_info.get_os_name())


@app.context_processor
def disk_usage_info():
    return dict(disk_usage_info=pi_sys_info.get_disk_usage_info())


@app.context_processor
def running_process_info():
    return dict(running_process_info=pi_sys_info.get_running_process_info())


@app.context_processor
def utility_processor():
    def short_date(a,b,c):
        return u'{0}{1}, {2}'.format(a, b,c)
    return dict(short_date=short_date)


if __name__ == "__main__":
    logger.info("Started")
    try:
        app.run(host="0.0.0.0", port=8443, debug=False)
    except KeyboardInterrupt:
        logger.info("Stopped")
        exit()
