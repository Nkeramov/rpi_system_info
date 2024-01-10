import os
import fcntl
import struct
import socket
import platform
import subprocess
from datetime import datetime

from flask import Flask, render_template
from flask_caching import Cache

config={
    'CACHE_TYPE': 'SimpleCache',
    "CACHE_DEFAULT_TIMEOUT": 300
}

app = Flask(__name__)

app.config.from_mapping(config)

cache = Cache(app)



def get_mac_address(interface='eth0'):
    """
	Return the MAC address of the specified interface
    """
    try:
        str = open('/sys/class/net/%s/address' %interface).read()
    except:
        str = "00:00:00:00:00:00"
    return str[0:17]


def get_ip_address(interface='eth0'):
    """
	Return the IP address of the specified interface
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sockfd = s.fileno()
        SIOCGIFADDR = 0x8915
        ifreq = struct.pack('16sH14s', interface.encode('utf-8'), socket.AF_INET, b'\x00'*14)
        res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
        ip = socket.inet_ntoa(struct.unpack('16sH2x4s8x', res)[2])
    except:
        ip = "0.0.0.0"
    return ip


def get_pi_model():
    pi_model = subprocess.check_output("cat /sys/firmware/devicetree/base/model", shell=True).decode().replace('\"', '')
    return pi_model


def cpu_generic_details():
    try:
        items = [s.decode().split('\t: ') for s in subprocess.check_output(["cat /proc/cpuinfo  | grep 'model name\|Hardware\|Serial' | uniq "], shell=True).splitlines()]
    except Exception as ex:
        print(ex)
    finally:
        return items


def disk_usage_list():
    try:
        items = [s.split() for s in subprocess.check_output(['df', '-h'], universal_newlines=True).splitlines()]
    except Exception as ex:
        print(ex)
    finally:
        return items[1:]


def running_process_list():
    items = []
    try:
        items = [s.decode().split() for s in subprocess.check_output(["ps -Ao user,pid,pcpu,pmem,comm,lstart --sort=-pcpu"], shell=True).splitlines()]
    except Exception as ex:
        print(ex)
    finally:
        return items[1:]


@app.route('/')
# cached for 60 seconds
@cache.cached(timeout=60)
def index():
    sys_data = {"current_time": '',"machine_name": ''}
    try:
        sys_data['current_time'] = datetime.now().strftime("%d-%b-%Y , %I : %M : %S %p")
        sys_data['machine_name'] =  platform.node()
        pi_model = get_pi_model()
        ip_address = get_ip_address()
        mac_address = get_mac_address()
        cpu_generic_info = cpu_generic_details()
        disk_usage_info = disk_usage_list()
        running_process_info = running_process_list()
    except Exception as ex:
        print(ex)
    finally:
        return render_template("index.html", title='Raspberry Pi System Info',
                                sys_data = sys_data,
                                pi_model = pi_model,
                                ip_address = ip_address,
                                mac_address = mac_address,
                                cpu_generic_info = cpu_generic_info,
                                disk_usage_info= disk_usage_info,
                                running_process_info = running_process_info)


@app.route('/restart')
def restart():
    os.system('sudo reboot now')


@app.route('/shutdown')
def shutdown():
    os.system('sudo stutdown now')


@app.context_processor
def boot_info():
    item = {'start_time': 'Na','running_since':'Na'}
    try:
        item['running_duration'] = subprocess.check_output(['uptime -p'], shell=True).decode()[3:]
        item['start_time'] = subprocess.check_output(['uptime -s'], shell=True).decode()
    except Exception as ex:
        print(ex)
    finally:
        return dict(boot_info = item)


@app.context_processor
def memory_usage_info():
    try:
        item = {'total': 0,'used': 0, 'free': 0,'available': 0 }
        item['total'] = subprocess.check_output(["free -m -t | awk 'NR==2' | awk '{print $2'}"], shell=True).decode()
        item['used'] = subprocess.check_output(["free -m -t | awk 'NR==2' | awk '{print $3'}"], shell=True).decode()
        item['free'] = subprocess.check_output(["free -m -t | awk 'NR==2' | awk '{print $4'}"], shell=True).decode()
        item['cache'] = subprocess.check_output(["free -m -t | awk 'NR==2' | awk '{print $6'}"], shell=True).decode()
        item['available'] = subprocess.check_output(["free -m -t | awk 'NR==2' | awk '{print $7'}"], shell=True).decode()
    except Exception as ex:
        print(ex)
    finally:
        return dict(memory_usage_info = item)


@app.context_processor
def os_name():
    os_info = subprocess.check_output("cat /etc/*-release | grep PRETTY_NAME | cut -d= -f2", shell=True).decode().replace('\"', '')
    return dict(os_name=os_info)


@app.context_processor
def cpu_usage_info():
    item = {'in_use': 0}
    try:
        item['in_use'] = subprocess.check_output("top -b -n2 | grep 'Cpu(s)'|tail -n 1 | awk '{print $2 + $4 }'", shell=True).decode()
    except Exception as ex:
        print(ex)
    finally:
        return dict(cpu_usage_info = item)


@app.context_processor
def cpu_processor_count():
    proc_info = subprocess.check_output("nproc", shell=True).decode().replace('\"', '')
    return dict(cpu_processor_count=proc_info)


@app.context_processor
def cpu_core_frequency():
    core_frequency = int(int(subprocess.check_output("vcgencmd measure_clock arm | cut -d= -f2", shell=True).decode().replace('\"', '')) // 1e6)
    return dict(cpu_core_frequency=core_frequency)


@app.context_processor
def cpu_core_volt():
    core_volt = subprocess.check_output("vcgencmd measure_volts| cut -d= -f2", shell=True).decode().replace('\"', '').strip()[:-1]
    return dict(cpu_core_volt=f"{float(core_volt): .3f}")


@app.context_processor
def cpu_temperature():
    cpuInfo = {'temperature': 0, 'color': 'white'}
    try:
        cpuTemp = float(subprocess.check_output(["vcgencmd measure_temp"], shell=True).decode().split('=')[1].split('\'')[0])
        cpuInfo['temperature']=cpuTemp
        if cpuTemp > 40 and cpuTemp < 50:
            cpuInfo['color'] = 'orange'
        elif cpuTemp > 50:
            cpuInfo['color'] = 'red'
        return cpuInfo
    except Exception as ex:
        print(ex)
    finally:
        return dict(cpu_temperature=cpuInfo)


@app.context_processor
def utility_processor():
    def short_date(a,b,c):
        return u'{0}{1}, {2}'.format(a, b,c)
    return dict(short_date=short_date)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443, debug=False)
