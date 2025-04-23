import re
import time
import logging
import subprocess
from datetime import datetime
from functools import cached_property
from typing import List, Dict, Tuple, Optional

from .cls_utils import Singleton
from .log_utils import LoggerSingleton


class PiSystemInfo(metaclass=Singleton):

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __get_shell_cmd_output(self, command: str) -> Optional[str]:
        """Executes a shell command and returns its standard output.

        This method runs the provided shell command using `subprocess.run`.
        It captures the standard output and standard error, and checks for
        execution errors. If the command is successful, the stripped standard
        output is returned. If the command fails (either due to a non-zero
        exit code or command not being found), an error is logged using the
        logger and `None` is returned.

        *Warning*: `shell=True` is used to execute the command with pipes.
        This can be a security risk if the `command` string is constructed
        from untrusted input, as it can lead to shell injection vulnerabilities.

        Args:
            command: The shell command to execute as a string.

        Returns:
            The stripped standard output of the command as a string if the
            command executes successfully, otherwise `None`.
        """
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Shell command '{command}' failed (code {e.returncode}): {e.stderr.strip()}")
        except FileNotFoundError:
            self.logger.error(f"Command not found: {command}")

    @cached_property
    def hostname(self) -> Optional[str]:
        """Retrieves the hostname using the 'hostname' command.

        Returns:
            The hostname, or None if the command fails.
        """
        command = "hostname"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def model(self) -> Optional[str]:
        """Retrieves the system model from /sys/firmware/devicetree/base/model.

        Returns:
            The system model, or None if the command fails or the file is not found.
        """
        command = "cat /sys/firmware/devicetree/base/model"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def os_name(self) -> Optional[str]:
        """Retrieves the pretty OS name from /etc/*-release.

        Returns:
            The pretty OS name, or None if the command fails.  Removes surrounding quotes.
        """
        command = "cat /etc/*-release | grep PRETTY_NAME | cut -d= -f2"
        return self.__get_shell_cmd_output(command).strip('"')

    @cached_property
    def cpu_model_name(self) -> Optional[str]:
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

    @cached_property
    def cpu_hardware_type(self) -> Optional[str]:
        """Retrieves the CPU hardware type from /proc/cpuinfo.

        Returns:
            The CPU hardware type, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Hardware' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_revision(self) -> Optional[str]:
        """Retrieves the CPU revision from /proc/cpuinfo.

        Returns:
            The CPU revision, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Revision' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_serial_number(self) -> Optional[str]:
        """Retrieves the CPU serial number from /proc/cpuinfo.

        Returns:
            The CPU serial number, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Serial' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_architecture(self) -> Optional[str]:
        """Retrieves the CPU architecture from lscpu.

        Returns:
            The CPU architecture, or None if the command fails.
        """
        command = "lscpu | grep 'Architecture' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_core_count(self) -> Optional[int]:
        """Retrieves the number of CPU cores using 'nproc'.

        Returns:
            The number of CPU cores, or None if the command fails.
        """
        command = "nproc"
        result = self.__get_shell_cmd_output(command)
        return int(result) if result is not None else result

    @cached_property
    def cpu_cache_sizes(self) -> Optional[str]:
        """Retrieves CPU cache sizes using the lscpu command.

        Returns:
            A dictionary {L1d: size, L1i: size, L2: size}, where size is a string representing value in KiB, or None if command fails.
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
        """Retrieves CPU frequency info in specified units (Hz, KHz, MHz or GHz).

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
                    self.logger.error(f"Requested unknown cpu frequency unit: {unit}")

    def get_cpu_usage(self) -> Optional[str]:
        """Retrieves the CPU usage using 'top'.

        Returns:
            The CPU usage, or None if the command fails. Note that the output format is dependent on 'top'.
        """
        command = "top -b -n2 | grep 'Cpu(s)'| tail -n 1 | awk '{print $2 + $4 }'"
        return self.__get_shell_cmd_output(command)

    def get_ram_info(self, unit: str = 'm') -> Optional[Dict[str, Optional[str]]]:
        """Retrieves RAM info in specified units (b, k, m, g). Uses a safer approach.

        Returns:
            The RAM info dict with total, used, free, cache and available memory volume in passed unit.
        """
        if unit not in ['b', 'k', 'm', 'g']:
            self.logger.error(f"Requested unknown ram volume unit: {unit}")
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
        except (IndexError, ValueError) as e:
            self.logger.error(f"Failed to parse 'free' command output: {output} ({e})")
        return None

    def get_mac_address(self, interface: str='eth0') -> Optional[str]:
        """Retrieves the MAC address for a specified network interface.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The MAC address, or None if the command fails or the interface is not found.
        """
        command = f"cat /sys/class/net/{interface}/address"
        address = self.__get_shell_cmd_output(command)
        return address.upper() if address is not None else None

    def get_ip_info(self, interface: str = 'eth0') -> Optional[Dict[str, Optional[str]]]:
        """Retrieves the IP information for a specified network interface.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The IP info dict with IP address, network mask, broadcast IP address,
            or None if the command fails or the interface is not connected.
        """
        command = f"ifconfig {interface} | grep 'inet '"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            fields = output.split()
            return {
                'ip': fields[1],
                'mask': fields[3],
                'broascast': fields[5],
            }
        except (IndexError, ValueError) as e:
            self.logger.error(f"Failed to parse 'ifconfig' command output: {output} ({e})")
        return None

    def get_bluetooth_mac_address(self) -> Optional[str]:
        """Retrieves the MAC address for the Bluetooth interface.

        Returns:
            The MAC address, or None if the command fails or the interface is not found.
        """
        command = f"hcitool dev"
        address = self.__get_shell_cmd_output(command).split('\n')[1].split()[1]
        return address.upper() if address is not None else None

    def get_available_wifi_networks(self) -> Optional[List[List[str]]]:
        """Retrieves info about available Wi-Fi networks.

        Returns:
            The Wi-Fi Networks info dict with ssid, bssid, mode, channel, rate, signal, bars and security fields.
            Wi-Fi networks in list ordered by SSID.
        """
        command = "nmcli dev wifi"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            lines = output.splitlines()[1:]
            if not lines:
                self.logger.warning("No Wi-Fi netwworks information available")
                return None
            networks = []
            for line in lines:
                values = line.split()
                k = values.index("Mbit/s")
                networks.append({
                    'ssid': " ".join(values[1:k-3]),
                    'bssid': values[0],
                    'mode': values[k-3],
                    'channel': values[k-2],
                    'rate': " ".join(values[k-1:k+1]),
                    'signal': values[k+1],
                    'bars': values[k+2],
                    'security': " ".join(values[k+3:])
                })
            return networks
        except Exception as e:
            self.logger.error(f"Unexpected error getting Wi-Fi networks info: {e}")
        return None

    def get_disk_usage_info(self) -> Optional[List[List[str]]]:
        """Retrieves disk usage info in human readable format.

        Returns:
            List of dictionaries with disk info or None if error occurs.
            Each dict contains: filesystem, size, used, available, use_percent, mounted_on
        """
        command = "df -h --output=source,size,used,avail,pcent,target | head -n 1; df -h | tail -n +2 | sort -k6"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            lines = output.splitlines()[1:]
            if not lines:
                self.logger.warning("No disk usage information available")
                return None
            headers = ["filesystem", "size", "used", "available", "use_percent", "mounted_on"]
            disks = []
            for line in lines:
                values = line.split()
                values = line.split(maxsplit=5)
                if len(values) != 6:
                    continue
                disk_info = dict(zip(headers, values))
                disk_info["use_percent"] = disk_info["use_percent"].replace("%", "")
                disks.append(disk_info)
            return disks
        except Exception as e:
            self.logger.error(f"Unexpected error getting disk info: {e}")
        return None

    def get_running_process_info(self) -> Optional[List[List[str]]]:
        """Retrieves info about running processes in system.

        Returns:
            List of process dictionaries or None if error occurs.
            Each dict contains: user, pid, cpu%, mem%, command, start_time
        """
        command = "ps -eo user,pid,pcpu,pmem,comm,lstart --sort=-pcpu"
        output = self.__get_shell_cmd_output(command)
        if output is None:
            return None
        try:
            lines = output.splitlines()[1:]
            if not lines:
                self.logger.warning("No processes information available")
                return None
            processes = []
            for line in lines:
                try:
                    parts = line.split()
                    process_info = {
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu_percent': float(parts[2]),
                        'mem_percent': float(parts[3]),
                        'command': " ".join(parts[4:-5]),
                        'started_on': datetime.strptime(" ".join(parts[-5:]), "%a %b %d %H:%M:%S %Y")
                    }
                    processes.append(process_info)
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Skipping malformed process line: {line} ({e})")
                    continue
            return processes
        except Exception as e:
            self.logger.error(f"Unexpected error getting process info: {e}")
        return None

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


if __name__ == "__main__":
    logger = LoggerSingleton(
        level="DEBUG",
        msg_format='%(asctime)s - %(levelname)s - %(message)s',
        date_format='%Y-%m-%d %H:%M:%S',
        colored=True
    ).get_logger()
    pi_sys_info = PiSystemInfo(logger)
    try:
        logger.info(f"Model: {pi_sys_info.get_model()}")
        logger.info(f"OS: {pi_sys_info.get_os_name()}")
        for interface in ['eth0', 'wlan0']:
            mac_address = pi_sys_info.get_mac_address(interface)
            ip_address = pi_sys_info.get_ip_info(interface)['ip']
            logger.info(f"{interface} interface: MAC address {mac_address}, IP address {ip_address}")
        while True:
            try:
                cpu_temp = pi_sys_info.get_cpu_temperature()
                cpu_freq = pi_sys_info.get_cpu_core_frequency()
                cpu_usage = pi_sys_info.get_cpu_usage()
                ram_info = pi_sys_info.get_ram_info()
                logger.info(f"CPU: temperature {cpu_temp} \xb0C, frequency {cpu_freq} MHz, usage {cpu_usage}%")
                logger.info(f"RAM: total {ram_info['total']} Mb, used {ram_info['used']} Mb, free {ram_info['free']} Mb, "
                            f"cache {ram_info['cache']} Mb, available {ram_info['available']} Mb")
            except Exception as e:
                logger.error("Error during system info retrieval: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error("Unhandled exception in main loop: {e}")
