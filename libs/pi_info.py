
import os
import re
import time
import logging
import subprocess
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Literal, Optional

from .cls_utils import Singleton
from .log_utils import LoggerSingleton



class ModelType(Enum):
    UNKNOWN = -100

    RPI_A = 0
    RPI_B = 1
    RPI_A_PLUS = 2
    RPI_B_PLUS = 3
    RPI_2B = 4
    RPI_ALPHA = 5
    RPI_CM1 = 6
    # 0x7 pass
    RPI_3B = 8
    RPI_ZERO = 9
    RPI_CM3 = 0xA
    # 0xb pass
    RPI_ZERO_W = 0xC
    RPI_3B_PLUS = 0xD
    RPI_3A_PLUS = 0xE
    # 0x0f: Internal use only
    RPI_CM3_PLUS = 0x10
    RPI_4B = 0x11
    RPI_Zero2W = 0x12
    RPI_400 = 0x13
    RPI_CM4 = 0x14
    RPI_CM4S = 0x15
    # 0x16: Internal use only
    RPI_5 = 0x17
    RPI_CM5 = 0x18
    RPI_CM5_LITE = 0x19


class IncorrectFrequencyUnitError(Exception):
    """Raise when frequncy unit not in ['Hz', 'KHz', 'MHz', 'GHz']"""


@dataclass(frozen=True)
class PiInfo(metaclass=Singleton):
    _NET_PATH = "/sys/class/net"
    logger: logging.Logger = field(repr=False)
    revision_code: str = field(init=False)
    revision: str = field(init=False)
    model_type: ModelType = field(init=False)
    manufacturer: str = field(init=False)
    cpu_model: str = field(init=False)
    memory_size: int = field(init=False)
    overvoltage_allowed: bool = field(init=False, default=False)
    otp_programming_allowed: bool = field(init=False, default=False)
    otp_reading_allowed: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.logger.debug("Fetching board revision code...")
        command = "cat /proc/cpuinfo | grep 'Revision' | cut -d: -f2"
        fetched_revision_code = self.__get_shell_cmd_output(command)
        self.logger.debug(f"Board revision code: {fetched_revision_code}")
        object.__setattr__(self, 'revision_code', fetched_revision_code)
        self.logger.debug("Parsing board revision code string...")
        decoded_data = PiInfo.decode_revision_code(fetched_revision_code)
        object.__setattr__(self, 'model_type', decoded_data['model_type'])
        object.__setattr__(self, 'revision', decoded_data['revision'])
        object.__setattr__(self, 'manufacturer', decoded_data['manufacturer'])
        object.__setattr__(self, 'cpu_model', decoded_data['cpu_model'])
        object.__setattr__(self, 'memory_size', decoded_data['memory_size'])
        if 'overvoltage_allowed' in decoded_data:
            object.__setattr__(self, 'overvoltage_allowed', decoded_data['overvoltage_allowed'])
        if 'otp_programming_allowed' in decoded_data:
            object.__setattr__(self, 'otp_programming_allowed', decoded_data['otp_programming_allowed'])
        if 'otp_reading_allowed' in decoded_data:
            object.__setattr__(self, 'otp_reading_allowed', decoded_data['otp_reading_allowed'])
        self.logger.info(f"Board info fully initialized")

    def __str__(self) -> str:
        return (f"Model: {self.model_name}, "
                f"Revision: {self.revision}, "
                f"Serial number: {self.serial_number}, "
                f"Manufacturer: {self.manufacturer}, "
                f"CPU model: {self.cpu_model}, "
                f"Memory size: {self.memory_size}Mb")

    @staticmethod
    def decode_revision_code(revision_code: str) -> dict[str, Any]:
        old_boards_revisions_decoder = {
            0x0000: (ModelType.UNKNOWN, "0.0", 0, "UNKNOWN", "UNKNOWN"),
            0x0002: (ModelType.RPI_B, "1.0", 256, "BCM2835", "EGOMAN"),
            0x0003: (ModelType.RPI_B, "1.0", 256, "BCM2835", "EGOMAN"),
            0x0004: (ModelType.RPI_B, "2.0", 256, "BCM2835", "SONY_UK"),
            0x0005: (ModelType.RPI_B, "2.0", 256, "BCM2835", "QISDA"),
            0x0006: (ModelType.RPI_B, "2.0", 256, "BCM2835", "EGOMAN"),
            0x0007: (ModelType.RPI_A, "2.0", 256, "BCM2835", "EGOMAN"),
            0x0008: (ModelType.RPI_A, "2.0", 256, "BCM2835", "SONY_UK"),
            0x0009: (ModelType.RPI_A, "2.0", 256, "BCM2835", "QISDA"),
            0x000D: (ModelType.RPI_B, "2.0", 512, "BCM2835", "EGOMAN"),
            0x000E: (ModelType.RPI_B, "2.0", 512, "BCM2835", "SONY_UK"),
            0x000F: (ModelType.RPI_B, "2.0", 512, "BCM2835", "EGOMAN"),
            0x0010: (ModelType.RPI_B_PLUS, "1.2", 512, "BCM2835", "SONY_UK"),
            0x0011: (ModelType.RPI_CM1, "1.0", 512, "BCM2835", "SONY_UK"),
            0x0012: (ModelType.RPI_A_PLUS, "1.1", 256, "BCM2835", "SONY_UK"),
            0x0013: (ModelType.RPI_B_PLUS, "1.2", 512, "BCM2835", "EMBEST"),
            0x0014: (ModelType.RPI_CM1, "1.0", 512, "BCM2835", "EMBEST"),
            0x0015: (ModelType.RPI_A_PLUS, "1.1", 512, "BCM2835", "EMBEST")
        }
        memory_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384]
        cpu_models = ["BCM2835", "BCM2836", "BCM2837", "BCM2711", "BCM2712"]
        manufacturers = ["Sony UK", "Egoman", "Embest", "Sony Japan", "Embest", "Stadium"]

        code = int(revision_code, 16)
        flag = (code & 0x800000) >> 23
        if flag:
            return {
                'model_type': ModelType((code & 0xFF0) >> 4),
                'revision':  f"1.{code & 0xF}",
                'memory_size': memory_sizes[(code & 0x700000) >> 20],
                'cpu_model': cpu_models[(code & 0xF000) >> 12],
                'manufacturer': manufacturers[(code & 0xF0000) >> 16],
                'overvoltage_allowed': bool((code & 0x80000000) >> 31),
                'otp_programming_allowed': bool((code & 0x40000000) >> 30),
                'otp_reading_allowed': bool((code & 0x20000000) >> 29),
            }
        else:
            return {
                'model_type': old_boards_revisions_decoder[code][0],
                'revision': old_boards_revisions_decoder[code][1],
                'memory_size': old_boards_revisions_decoder[code][2],
                'cpu_model': old_boards_revisions_decoder[code][3],
                'manufacturer': old_boards_revisions_decoder[code][4]
            }

    @staticmethod
    def float_to_int_if_zero_fraction(x: float) -> float | int:
        """Converts a real number to an integer if its fractional part is zero.
            Otherwise, returns the passed value.
        """
        if isinstance(x, float):
            if x.is_integer():
                return int(x)
            else:
                return x
        else:
            raise TypeError("Floating point number expected")

    @staticmethod
    def convert_frequency(frequency: float, unit: Literal['Hz', 'KHz', 'MHz', 'GHz'] = 'MHz') -> float | int:
        result = 0.0
        match unit:
            case 'Hz':
                result = frequency
            case 'KHz':
                result = frequency / 10**3
            case 'MHz':
                result = frequency / 10**6
            case 'GHz':
                result = frequency / 10**9
            case _:
                raise IncorrectFrequencyUnitError(f"Requested unknown CPU frequency unit: {unit}")
        return PiInfo.float_to_int_if_zero_fraction(result)

    def __get_shell_cmd_output(self, command: str) -> str:
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
        return ''

    @cached_property
    def model_name(self) -> str:
        """Retrieves the board model name from /sys/firmware/devicetree/base/model.

        Returns:
            The board model name, or None if the command fails or the file is not found.
        """
        command = "cat /sys/firmware/devicetree/base/model"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def serial_number(self) -> str:
        """Retrieves the board serial number from /proc/cpuinfo.

        Returns:
            The board serial number, or None if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Serial' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_architecture(self) -> str:
        """Retrieves the CPU architecture from lscpu.

        Returns:
            The CPU architecture, or None if the command fails.
        """
        command = "lscpu | grep 'Architecture' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_cores_count(self) -> int:
        """Retrieves the number of CPU cores using 'nproc'.

        Returns:
            The number of CPU cores, or 0 if the command fails.
        """
        command = "nproc"
        result = self.__get_shell_cmd_output(command)
        try:
            return int(result)
        except ValueError as e:
            self.logger.error(f"Error while converting number of cores to int: {result}")
        return 0

    @cached_property
    def cpu_cache_sizes(self) -> dict[str, str]:
        """Retrieves CPU cache sizes using the lscpu command.

        Returns:
            A dictionary {L1d: size, L1i: size, L2: size}, where size is a string representing value in KiB, or None if command fails.
        """
        command = "lscpu"
        output = self.__get_shell_cmd_output(command)
        cache_types = ["L1d", "L1i", "L2"]
        cache_sizes = {cache: "" for cache in cache_types}
        if output:
            lines = output.splitlines()
            for line in lines:
                for cache in cache_types:
                    match = re.match(fr"{cache} cache:\s*(\S+)", line)
                    if match:
                        cache_sizes[cache] = match.group(1)
                        continue
        return cache_sizes

    @cached_property
    def hostname(self) -> str:
        """Retrieves the hostname using the 'hostname' command.

        Returns:
            The hostname, or None if the command fails.
        """
        command = "hostname"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def os_name(self) -> str:
        """Retrieves the pretty OS name from /etc/*-release.

        Returns:
            The pretty OS name, or None if the command fails.  Removes surrounding quotes.
        """
        command = "cat /etc/*-release | grep PRETTY_NAME | cut -d= -f2"
        return self.__get_shell_cmd_output(command).strip('"')

    def get_cpu_core_voltage(self) -> Optional[float]:
        """Retrieves the CPU core voltage using 'vcgencmd'.

        Returns:
            The CPU core voltage, or None if the command fails.
        """
        command = "vcgencmd measure_volts| cut -d= -f2"
        result = self.__get_shell_cmd_output(command)
        try:
            if result is not None:
                return float(result[:-1])
        except (IndexError, ValueError) as e:
            self.logger.error(f"Error while converting CPU voltage to float, voltage value: {result}")
        return None

    def get_cpu_temperature(self) -> Optional[float]:
        """Retrieves the CPU temperature using 'vcgencmd'.

        Returns:
            The CPU temperature, or None if the command fails.
        """
        command = "vcgencmd measure_temp | cut -d= -f2 | cut -d\\' -f1"
        result = self.__get_shell_cmd_output(command)
        try:
            if result is not None:
                return float(result)
        except ValueError as e:
            self.logger.error(f"Error while converting CPU temperature to float, temperature value: {result}")
        return None

    def get_cpu_core_frequencies(self, unit: Literal['Hz', 'KHz', 'MHz', 'GHz'] = 'MHz') -> dict[str, int | float]:
        """Retrieves min, max and current CPU core frequencies in specified units (Hz, KHz, MHz or GHz).
        If for some frequency type the command failss, then 0 will return for it.

        Args:
            unit: The desired unit for the core frequency (Hz, KHz, MHz, GHz). Defaults to 'MHz'.

        Returns:
            Dict with CPU core frequencies values in the specified unit.
        """
        core_frequencies = {
            'min': 0.0,
            'max': 0.0,
            'cur': 0.0
        }
        for ft in core_frequencies:
            command = f"cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_{ft}_freq"
            result = self.__get_shell_cmd_output(command)
            if result:
                try:
                    frequency = float(result) * 1000
                    core_frequencies[ft] = PiInfo.convert_frequency(frequency, unit)
                except ValueError as e:
                    self.logger.error(f"Error while converting CPU frequency to float, frequency value: {result}")
                except Exception as e:
                    self.logger.error(f"CPU frequency processing error: {e}")
        self.logger.info(core_frequencies)
        return core_frequencies

    def get_cpu_usage(self) -> str:
        """Retrieves the CPU usage using 'top'.

        Returns:
            The CPU usage, or None if the command fails. Note that the output format is dependent on 'top'.
        """
        command = "top -b -n2 | grep 'Cpu(s)'| tail -n 1 | awk '{print $2 + $4 }'"
        return self.__get_shell_cmd_output(command)

    def get_ram_info(self, unit: str = 'm') -> dict[str, str]:
        """Retrieves RAM info in specified units (b, k, m, g). Uses a safer approach.

        Returns:
            The RAM info dict with total, used, free, cache and available memory volume in passed unit.
        """
        ram_fields = ['total', 'used', 'free', 'cache', 'available']
        ram_info = {field: "" for field in ram_fields}
        ram_info['size'] = str(self.memory_size)
        if unit not in ['b', 'k', 'm', 'g']:
            self.logger.error(f"Requested unknown RAM volume unit: {unit}")
            return ram_info
        command = f"free -{unit}"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()
                fields = lines[1].split()
                ram_info['total'] = fields[1]
                ram_info['used'] = fields[2]
                ram_info['free'] = fields[3]
                ram_info['cache'] = fields[5]
                ram_info['available'] = fields[6]
            except (IndexError, ValueError) as e:
                self.logger.error(f"Failed to parse 'free' command output: {output} ({e})")
        return ram_info

    def get_mac_address(self, interface: str='eth0') -> Optional[str]:
        """Retrieves the MAC address for a specified network interface.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The MAC address, or None if the command fails or the interface is not found.
        """
        try:
            if interface in os.listdir(self._NET_PATH):
                command = f"cat /sys/class/net/{interface}/address"
                address = self.__get_shell_cmd_output(command)
                return address.upper()
            else:
                self.logger.error(f"Incorrect network interface: {interface}")
        except FileNotFoundError:
            self.logger.error(f"Can not load network interface info from {self._NET_PATH}")
        return None

    def get_ip_info(self, interface: str = 'eth0') -> Optional[dict[str, str]]:
        """Retrieves the IP information for a specified network interface.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The IP info dict with IP address, network mask, broadcast IP address,
            or None if the command fails or the interface is not connected.
        """
        try:
            if interface in os.listdir(self._NET_PATH):
                command = f"ifconfig {interface} | grep 'inet '"
                output = self.__get_shell_cmd_output(command)
                if output:
                    try:
                        fields = output.split()
                        return {
                            'ip': fields[1],
                            'mask': fields[3],
                            'broadscast': fields[5],
                        }
                    except (IndexError, ValueError) as e:
                        self.logger.error(f"Failed to parse 'ifconfig' command output: {output} ({e})")
            else:
                self.logger.error(f"Incorrect network interface: {interface}")
        except FileNotFoundError:
            self.logger.error(f"Can not load network interface info from {self._NET_PATH}")
        return None

    def get_bluetooth_mac_address(self) -> Optional[str]:
        """Retrieves the MAC address for the Bluetooth interface.

        Returns:
            The MAC address, or None if the command fails or the interface is not found.
        """
        command = f"hcitool dev"
        address = self.__get_shell_cmd_output(command)
        if address:
            try:
                address = address.split('\n')[1].split()[1]
                return address.upper()
            except (IndexError, ValueError) as e:
                self.logger.error(f"Failed to parse 'hcitool dev' command output: {address} ({e})")
        return None

    def get_available_wifi_networks(self) -> list[dict[str, str]]:
        """Retrieves info about available Wi-Fi networks.

        Returns:
            The Wi-Fi Networks info dict with ssid, bssid, mode, channel, rate, signal, bars and security fields.
            Wi-Fi networks in list ordered by SSID.
        """
        networks: list[dict[str, str]] = []
        command = "nmcli dev wifi"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()[1:]
                if not lines:
                    self.logger.warning("No Wi-Fi networks information available")
                    return networks
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
        return networks

    def get_disks_info(self) -> list[dict[str, str]]:
        """Retrieves disk info in human readable format.

        Returns:
            List of dictionaries with disk info or None if error occurs.
            Each dict contains: filesystem, size, used, available, use_percent, mounted_on
        """
        headers = ["filesystem", "size", "used", "available", "use_percent", "mounted_on"]
        disks: list[dict[str, str]] = []
        command = "df -h --output=source,size,used,avail,pcent,target | head -n 1; df -h | tail -n +2 | sort -k6"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()[1:]
                if not lines:
                    self.logger.warning("No disk usage information available")
                    return disks
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
        return disks

    def get_processes_info(self) -> list[dict[str, Any]]:
        """Retrieves info about running processes in system.

        Returns:
            List of process dictionaries or None if error occurs.
            Each dict contains: user, pid, cpu%, mem%, command, start_time
        """
        processes: list[dict[str, Any]] = []
        command = "ps -eo user,pid,pcpu,pmem,comm,lstart --sort=-pcpu"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()[1:]
                if not lines:
                    self.logger.warning("No processes information available")
                    return processes
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
        return processes

    def get_uptime_since(self) -> Optional[datetime]:
        """Retrieves the system uptime since boot, in YYYY-MM-DD HH:MM:SS format using 'uptime -s'.

        Returns:
            The uptime since boot, or None if the command fails.
        """
        command = "uptime -s"
        uptime_str = self.__get_shell_cmd_output(command)
        return datetime.strptime(uptime_str, "%Y-%m-%d %H:%M:%S")

    def get_uptime_pretty(self) -> str:
        """Retrieves the system uptime in a human-readable format using 'uptime -p'.

        Returns:
            The pretty uptime, or None if the command fails.
        """
        command = "uptime -p"
        return self.__get_shell_cmd_output(command)


def main() -> None:
    logger = LoggerSingleton(
        level="DEBUG",
        colored=True
    ).get_logger()
    pi_info = PiInfo(logger)
    print(pi_info)

    return
    try:
        logger.info(f"Model: {pi_info.model}")
        logger.info(f"OS: {pi_info.os_name}")
        for interface in ['eth0', 'wlan0']:
            mac_address = pi_info.get_mac_address(interface)
            ip_address = pi_info.get_ip_info(interface)['ip']
            logger.info(f"{interface} interface: MAC address {mac_address}, IP address {ip_address}")
        while True:
            try:
                cpu_temp = pi_info.get_cpu_temperature()
                cpu_freq = pi_info.get_cpu_core_frequency()
                cpu_usage = pi_info.get_cpu_usage()
                ram_info = pi_info.get_ram_info()
                logger.info(f"CPU: temperature {cpu_temp} \xb0C, frequency {cpu_freq} MHz, usage {cpu_usage}%")
                logger.info(f"RAM: total {ram_info['total']} Mb, used {ram_info['used']} Mb, free {ram_info['free']} Mb, "
                            f"cache {ram_info['cache']} Mb, available {ram_info['available']} Mb")
            except Exception as e:
                logger.error("Error during system info retrieval: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception in main loop: {e}")



if __name__ == "__main__":
    main()
