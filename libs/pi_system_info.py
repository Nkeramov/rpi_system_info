import os
import time
import logging
import subprocess


class PiSystemInfo:

    def __init__(self, logger):
        self.logger = logger

    def __get_shell_cmd_output(self, cmd: str) -> str | None:
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            output, error = process.communicate()
            return output.decode().strip()
        except Exception as error:
            logger.error(error)

    def get_hostname(self) -> str | None:
        command = "hostname"
        return self.__get_shell_cmd_output(command)

    def get_model(self) -> str | None:
        command = "cat /sys/firmware/devicetree/base/model"
        return self.__get_shell_cmd_output(command)

    def get_os_name(self) -> str | None:
        command = "cat /etc/*-release | grep PRETTY_NAME | cut -d= -f2"
        return self.__get_shell_cmd_output(command).strip('"')

    def get_uptime_since(self) -> str | None:
        command = "uptime -s"
        return self.__get_shell_cmd_output(command)

    def get_uptime_pretty(self) -> str | None:
        command = "uptime -p"
        return self.__get_shell_cmd_output(command)

    def get_mac_address(self, interface='eth0') -> str | None:
        command = f"cat /sys/class/net/{interface}/address"
        return self.__get_shell_cmd_output(command)

    def get_ip_address(self, interface='eth0') -> str | None:
        command = f"ifconfig {interface} | grep 'inet ' | awk '{{print $2}}'"
        return self.__get_shell_cmd_output(command)

    def get_cpu_model_name(self):
        command = "cat /proc/cpuinfo  | grep 'model name' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_hardware_type(self):
        command = "cat /proc/cpuinfo  | grep 'Hardware' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_revision(self):
        command = "cat /proc/cpuinfo  | grep 'Revision' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_serial_number(self):
        command = "cat /proc/cpuinfo  | grep 'Serial' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)


    def get_cpu_core_count(self) -> int | None:
        command = "nproc"
        result = self.__get_shell_cmd_output(command)
        return int(result) if result is not None else result

    def get_cpu_core_voltage(self) -> float | None:
        command = "vcgencmd measure_volts| cut -d= -f2"
        result = self.__get_shell_cmd_output(command)
        return float(result[:-1]) if result is not None else result

    def get_cpu_temperature(self) -> float | None:
        command = "vcgencmd measure_temp | cut -d= -f2 | cut -d\\' -f1"
        result = self.__get_shell_cmd_output(command)
        return float(result) if result is not None else result

    def get_cpu_core_frequency(self, unit: str = 'MHz') -> int | None:
        ''' Returns CPU frequency info in specified units (Hz, KHz, MHz or GHz)'''
        command = "vcgencmd measure_clock arm | cut -d= -f2"
        result = self.__get_shell_cmd_output(command)
        if result is not None:
            frequency = int(result)
            match unit:
                case 'Hz':
                    return frequency
                case 'KHz':
                    return frequency // 10**3
                case 'MHz':
                    return frequency // 10**6
                case 'GHz':
                    return frequency // 10**9
                case _:
                    logger.error(f"Requested unknown cpu frequency unit: {unit}")
                    return None
        else:
            return None

    def get_cpu_usage(self) -> str | None:
        command = "top -b -n2 | grep 'Cpu(s)'|tail -n 1 | awk '{print $2 + $4 }'"
        return self.__get_shell_cmd_output(command)

    def get_ram_info(self, unit: str = 'm') -> dict[str | None] | None:
        ''' Returns RAM info in specified units (b, k, m and g)'''
        if unit in ['b', 'k', 'm', 'g']:
            ram_info = dict()
            ram_info['total'] = self.__get_shell_cmd_output(f"free -{unit} | awk 'NR==2' | awk '{{print $2'}}")
            ram_info['used'] = self.__get_shell_cmd_output(f"free -{unit} | awk 'NR==2' | awk '{{print $3'}}")
            ram_info['free'] = self.__get_shell_cmd_output(f"free -{unit} | awk 'NR==2' | awk '{{print $4'}}")
            ram_info['cache'] = self.__get_shell_cmd_output(f"free -{unit} | awk 'NR==2' | awk '{{print $6'}}")
            ram_info['available'] = self.__get_shell_cmd_output(f"free -{unit} | awk 'NR==2' | awk '{{print $7'}}")
            return ram_info
        else:
            logger.error(f"Requested unknown ram volume unit: {unit}")
            return None

    def get_disk_usage_info(self) -> list | None:
        command = "df -h"
        result = self.__get_shell_cmd_output(command)
        return [s.split() for s in result.splitlines()[1:]]

    def get_running_process_info(self) -> list | None:
        command = "ps -Ao user,pid,pcpu,pmem,comm,lstart --sort=-pcpu"
        result = self.__get_shell_cmd_output(command)
        return [s.split() for s in result.splitlines()[1:]]



def get_console_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


if __name__ == "__main__":
    logger = get_console_logger()
    pi_sys_info = PiSystemInfo(logger)
    try:
        logger.info(f"Model : {pi_sys_info.get_model()}")
        logger.info(f"MAC address : {pi_sys_info.get_mac_address('eth0')}")
        logger.info(f"IP address : {pi_sys_info.get_ip_address('eth0')}")
        while(True):
            logger.info(f"CPU: temperature {pi_sys_info.get_cpu_temperature()} \xb0C, frequency {pi_sys_info.get_cpu_frequency()} MHz, usage {pi_sys_info.get_cpu_usage()}%")
            ram_info = pi_sys_info.get_ram_info()
            logger.info(f"RAM: total {ram_info['total']} Mb, used {ram_info['used']} Mb, free {ram_info['free']} Mb")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopped...")
