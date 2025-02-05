import re
import time
import logging
import subprocess
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class PiSystemInfo(object):

    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(PiSystemInfo, cls).__new__(cls)
        return cls.__instance

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __get_shell_cmd_output(self, command: str) -> Optional[str]:
        """Executes a shell command and returns its output. Handles errors."""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Shell command '{command}' failed: {e}")
        except FileNotFoundError:
            self.logger.error(f"Command not found: {command}")

    def get_hostname(self) -> Optional[str]:
        """Retrieves the hostname using the 'hostname' command.

        Returns:
            The hostname, or None if the command fails.
        """
        command = "hostname"
        return self.__get_shell_cmd_output(command)

    def get_model(self) -> Optional[str]:
        """Retrieves the system model from /sys/firmware/devicetree/base/model.

        Returns:
            The system model, or None if the command fails or the file is not found.
        """
        command = "cat /sys/firmware/devicetree/base/model"
        return self.__get_shell_cmd_output(command)

    def get_os_name(self) -> Optional[str]:
        """Retrieves the pretty OS name from /etc/*-release.

        Returns:
            The pretty OS name, or None if the command fails.  Removes surrounding quotes.
        """
        command = "cat /etc/*-release | grep PRETTY_NAME | cut -d= -f2"
        return self.__get_shell_cmd_output(command).strip('"')

    def get_uptime_since(self) -> Optional[datetime]:
        """Retrieves the system uptime since boot, in YYYY-MM-DD HH:MM:SS format using 'uptime -s'.

        Returns:
            The uptime since boot, or None if the command fails.
        """
        command = "uptime -s"
        uptime_str = self.__get_shell_cmd_output(command)
        return datetime.strptime(uptime_str, "%Y-%m-%d %H:%M:%S")

    def get_uptime_pretty(self) -> Optional[str]:
        """Retrieves the system uptime in a human-readable format using 'uptime -p'.

        Returns:
            The pretty uptime, or None if the command fails.
        """
        command = "uptime -p"
        return self.__get_shell_cmd_output(command)

    def get_mac_address(self, interface='eth0') -> Optional[str]:
        """Retrieves the MAC address for a specified network interface.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The MAC address, or None if the command fails or the interface is not found.
        """
        command = f"cat /sys/class/net/{interface}/address"
        address = self.__get_shell_cmd_output(command)
        return address.upper() if address is not None else None

    def get_ip_address(self, interface: str = 'eth0') -> Optional[str]:
        """Retrieves the IP address for a specified network interface.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The IP address, or None if the command fails or the interface is not found.
        """
        command = f"ifconfig {interface} | grep 'inet ' | awk '{{print $2}}'"
        return self.__get_shell_cmd_output(command)

    def get_bluetooth_mac_address(self) -> Optional[str]:
        """Retrieves the MAC address for the Bluetooth interface.

        Returns:
            The MAC address, or None if the command fails or the interface is not found.
        """
        command = f"hcitool dev"
        address = self.__get_shell_cmd_output(command).split('\n')[1].split()[1]
        return address.upper() if address is not None else None

    def get_cpu_model_name(self) -> Optional[str]:
        """Retrieves the CPU model name from /proc/cpuinfo.

        Returns:
            The CPU model name, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'model name' | cut -d: -f2"
        model =  self.__get_shell_cmd_output(command)
        if not model:
            command = "lscpu | grep 'Model name' | cut -d: -f2"
            model = self.__get_shell_cmd_output(command)
        return model

    def get_cpu_hardware_type(self) -> Optional[str]:
        """Retrieves the CPU hardware type from /proc/cpuinfo.

        Returns:
            The CPU hardware type, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Hardware' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_revision(self) -> Optional[str]:
        """Retrieves the CPU revision from /proc/cpuinfo.

        Returns:
            The CPU revision, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Revision' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_serial_number(self) -> Optional[str]:
        """Retrieves the CPU serial number from /proc/cpuinfo.

        Returns:
            The CPU serial number, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Serial' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_architecture(self) -> Optional[str]:
        """Retrieves the CPU architecture from lscpu.

        Returns:
            The CPU architecture, or None if the command fails.
        """
        command = "lscpu | grep 'Architecture' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    def get_cpu_core_count(self) -> Optional[int]:
        """Retrieves the number of CPU cores using 'nproc'.

        Returns:
            The number of CPU cores, or None if the command fails.
        """
        command = "nproc"
        result = self.__get_shell_cmd_output(command)
        return int(result) if result is not None else result

    def get_cpu_core_voltage(self) -> Optional[float]:
        """Retrieves the CPU core voltage using 'vcgencmd'.

        Returns:
            The CPU core voltage, or None if the command fails.
        """
        command = "vcgencmd measure_volts| cut -d= -f2"
        result = self.__get_shell_cmd_output(command)
        return float(result[:-1]) if result is not None else result

    def get_cpu_temperature(self) -> Optional[float]:
        """Retrieves the CPU temperature using 'vcgencmd'.

        Returns:
            The CPU temperature, or None if the command fails.
        """
        command = "vcgencmd measure_temp | cut -d= -f2 | cut -d\\' -f1"
        result = self.__get_shell_cmd_output(command)
        return float(result) if result is not None else result

    def get_cpu_core_frequency(self, unit: str = 'MHz') -> Optional[int]:
        """Returns CPU frequency info in specified units (Hz, KHz, MHz or GHz).

        Args:
            unit: The desired unit for the frequency (Hz, KHz, MHz, GHz). Defaults to 'MHz'.

        Returns:
            The CPU core frequency in the specified unit, or None if the command fails or the unit is invalid.
        """
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

    def get_cpu_usage(self) -> Optional[str]:
        """Retrieves the CPU usage using 'top'.

        Returns:
            The CPU usage, or None if the command fails. Note that the output format is dependent on 'top'.
        """
        command = "top -b -n2 | grep 'Cpu(s)'| tail -n 1 | awk '{print $2 + $4 }'"
        return self.__get_shell_cmd_output(command)

    def get_cpu_cache_sizes(self) -> Optional[str]:
        """Calls the lscpu command and returns a dictionary containing the sizes of L1d, L1i, L2 caches in KiB.

        Returns:
            A dictionary {L1d: size, L1i: size, L2: size}, where size is a string, or None if command fails.
        """
        command = "lscpu"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        cache_types = ["L1d", "L1i", "L2"]
        cache_sizes = {cache: "" for cache in cache_types}
        lines = output.splitlines()
        for line in lines:
            for cache in cache_types:
                match = re.match(fr"{cache} cache:\s*(\S+)", line)
                if match:
                    cache_sizes[cache] = match.group(1)
                    continue
        return cache_sizes

    def get_ram_info(self, unit: str = 'm') -> Optional[Dict[str, Optional[str]]]:
        """Returns RAM info in specified units (b, k, m, g). Uses a safer approach.

        Return:
            The RAM info dict with total, used, free, cache and available memory volume in passed unit.
        """
        if unit not in ['b', 'k', 'm', 'g']:
            logger.error(f"Requested unknown ram volume unit: {unit}")
            return None

        command = f"free -{unit}"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None

        try:
            lines = output.splitlines()
            fields = lines[1].split()
            return {
                'total': fields[1],
                'used': fields[2],
                'free': fields[3],
                'cache': fields[5],
                'available': fields[6],
            }
        except (IndexError, ValueError):
            logger.error(f"Failed to parse 'free' command output: {output}")
            return None

    def get_disk_usage_info(self) -> Optional[List[List[str]]]:
        """Returns disk usage info in human readable format.

        Return:
            The Disk info dict with filesystem, size, used, available, use percent and mounted on fields.
        """
        command = "df -h"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            lines = output.splitlines()[1:]
            result = []
            for line in lines:
                values = line.split()
                result.append({
                    'filesystem': values[0],
                    'size': values[1],
                    'used': values[2],
                    'available': values[3],
                    'use_percent': values[4],
                    'mounted_on': values[5]
                })
            return result
        except IndexError:
            logger.error(f"Failed to parse 'df' command output: {output}")
            return None

    def get_running_process_info(self) -> Optional[List[List[str]]]:
        """Returns info about running processes in system.

        Return:
            The Processes info dict with user, process id, cpu and memory use percent, command and started on fields.
        """
        command = "ps -Ao user,pid,pcpu,pmem,comm,lstart --sort=-pcpu"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            lines = output.splitlines()[1:]
            result = []
            for line in lines:
                values = line.split()
                cmd =  " ".join(values[4:-5])
                datetime_string = " ".join(values[-4:])
                datetime_object = datetime.strptime(datetime_string, "%b %d %H:%M:%S %Y")
                result.append({
                    'user': values[0],
                    'process_id': values[1],
                    'cpu_use_percent': values[2],
                    'memory_use_percent': values[3],
                    'command': cmd,
                    'started_on': datetime_object
                })
            return result
        except IndexError:
            logger.error(f"Failed to parse 'ps' command output: {output}")
            return None

    def get_available_wifi_networks(self) -> Optional[List[List[str]]]:
        """Returns info about available WiFi networks.

        Return:
            The WiFi Networks info dict with ssid, bssid, mode, channel, rate, signal, bars and security fields.
            WiFi networks in list ordered by SSID.
        """
        command = "nmcli dev wifi"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            lines = output.splitlines()[1:]
            result = []
            for line in lines:
                values = line.split()
                k = values.index("Mbit/s")
                result.append({
                    'ssid': " ".join(values[1:k-3]),
                    'bssid': values[0],
                    'mode': values[k-3],
                    'channel': values[k-2],
                    'rate': " ".join(values[k-1:k+1]),
                    'signal': values[k+1],
                    'bars': values[k+2],
                    'security': " ".join(values[k+3:])
                })
            return result
        except IndexError:
            logger.error(f"Failed to parse 'nmcli' command output: {output}")
            return None


def get_console_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


if __name__ == "__main__":
    logger = get_console_logger()
    pi_sys_info = PiSystemInfo(logger)
    try:
        logger.info(f"Model: {pi_sys_info.get_model()}")
        logger.info(f"IP address: {pi_sys_info.get_ip_address('eth0')}")
        logger.info(f"MAC address: {pi_sys_info.get_mac_address('eth0')}")
        while True:
            logger.info(f"CPU: temperature {pi_sys_info.get_cpu_temperature()} \xb0C, "
                        f"frequency {pi_sys_info.get_cpu_core_frequency()} MHz, usage {pi_sys_info.get_cpu_usage()}%")
            ram_info = pi_sys_info.get_ram_info()
            logger.info(f"RAM: total {ram_info['total']} Mb, used {ram_info['used']} Mb, free {ram_info['free']} Mb")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopped...")
