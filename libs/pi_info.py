import os
import re
import time
import socket
import logging
import subprocess
import http.client
import urllib.error
import urllib.request
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
    FrequencyUnit = Literal['Hz', 'KHz', 'MHz', 'GHz']

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
    def convert_frequency(frequency: float, unit: FrequencyUnit = 'MHz') -> float | int:
        """Converts input frequency value from Hz to specified unit."""
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

    @cached_property
    def boot_time(self) -> Optional[datetime]:
        """Retrieves the time of boot from which uptime is calculated.

        Returns:
            The datetime of boot or None if the command fails.
        """
        command = "uptime -s"
        uptime_str = self.__get_shell_cmd_output(command)
        if uptime_str:
            return datetime.strptime(uptime_str, "%Y-%m-%d %H:%M:%S")
        else:
            return None

    def get_uptime_pretty(self) -> str:
        """Retrieves the system uptime in a human-readable format.

        Returns:
            The uptime in human-readable format or empty string if the command fails.
        """
        command = "uptime -p"
        return self.__get_shell_cmd_output(command)

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

    def get_cpu_core_frequencies(self, unit: FrequencyUnit = 'MHz') -> dict[str, int | float]:
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

    def get_network_interface_info(self, interface: str='eth0') -> dict[str, str]:
        """Retrieves network interface info. Uses a safer approach.

        Args:
            interface: The network interface name (default: 'eth0').

        Returns:
            The network interface info dict with mac address, ip addres, network mask,
            broadcast ip address, default gateway ip address and state.
        """
        nic_fields = ['mac', 'ip', 'mask', 'broadcast', 'gateway', 'state']
        nic_info = {field: "" for field in nic_fields}
        try:
            if interface in os.listdir(self._NET_PATH):
                try:
                    mac_addr_cmd = f"cat /sys/class/net/{interface}/address"
                    mac_addr_output = self.__get_shell_cmd_output(mac_addr_cmd)
                    nic_info['mac'] = mac_addr_output.upper()

                    ip_link_cmd = f"ip -o link show {interface}"
                    ip_link_output = self.__get_shell_cmd_output(ip_link_cmd)
                    if "state UP" not in ip_link_output and "LOWER_UP" not in ip_link_output:
                        nic_info['state'] = 'DOWN'
                        self.logger.warning(f"Interface {interface} is DOWN")
                        return nic_info

                    nic_info['state'] = 'UP'
                    ip_addr_cmd = f"ip -4 addr show {interface}"
                    ip_addr_output = self.__get_shell_cmd_output(ip_addr_cmd)
                    ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', ip_addr_output)
                    broadcast_match = re.search(r'brd (\d+\.\d+\.\d+\.\d+)', ip_addr_output)
                    if not ip_match or not broadcast_match:
                        self.logger.error(f"Failed to parse 'ip addr' command output: {ip_addr_output}")
                    else:
                        nic_info['ip'] = ip_match.group(1)
                        prefix_len = int(ip_match.group(2))
                        nic_info['broadcast'] = broadcast_match.group(1)
                        mask = (0xffffffff << (32 - prefix_len)) & 0xffffffff
                        mask_bytes = [
                            (mask >> 24) & 0xff,
                            (mask >> 16) & 0xff,
                            (mask >> 8) & 0xff,
                            mask & 0xff
                        ]
                        nic_info['mask'] = ".".join(map(str, mask_bytes))

                        ip_route_cmd = f"ip route show | grep ^def.*{interface}"
                        ip_route_output = self.__get_shell_cmd_output(ip_route_cmd)
                        gateway_match = re.search(rf'^default via (\d+\.\d+\.\d+\.\d+)', ip_route_output)
                        if gateway_match:
                            nic_info['gateway'] = gateway_match.group(1)
                except Exception as e:
                    self.logger.error(f"Unexpected error while retrieving interface {interface} information: {e}")
            else:
                self.logger.error(f"Incorrect network interface: {interface}")
        except FileNotFoundError:
            self.logger.error(f"Can not load network interface info from {self._NET_PATH}")
        return nic_info

    def get_bluetooth_mac_address(self) -> str:
        """Retrieves the MAC address for the Bluetooth interface.

        Returns:
            The MAC address, or  if the command fails or the interface is not found.
        """
        command = "hcitool dev"
        address = self.__get_shell_cmd_output(command)
        if address:
            try:
                address = address.split('\n')[1].split()[1]
                return address.upper()
            except (IndexError, ValueError) as e:
                self.logger.error(f"Failed to parse {command} command output: {address} ({e})")
        return ''

    def get_available_wifi_networks(self) -> list[dict[str, str]]:
        """Retrieves info about available Wi-Fi networks.

        Returns:
            The Wi-Fi Networks info dict with ssid, bssid, mode, channel, rate, signal, bars and security fields.
            Wi-Fi networks in list ordered by SSID.
        """
        networks: list[dict[str, str]] = []
        command = "nmcli dev wifi list"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()[1:]
                if not lines:
                    self.logger.warning("No Wi-Fi networks information available")
                    return networks
                for line in lines:
                    values = line.split()
                    if line.startswith('*'):
                        values = values[1:]
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
                self.logger.error(f"Unexpected error while retrieving Wi-Fi networks info: {e}")
        return networks

    def get_wifi_network_name(self) -> str:
        """Retrieves the name of the wireless network to which the Raspberry Pi is connected.

        Returns:
            The Wi-Fi network name, or empty string if unable to obtain.
        """
        command = "iwgetid -r"
        return self.__get_shell_cmd_output(command)

    def check_internet_connection(self, test_url: str = "http://www.google.com", timeout: int = 5) -> bool:
        """Checks for an active internet connection by attempting to make an HTTP request.

        Args:
            test_url: URL to test the connection to. Defaults to "http://www.google.com".
            timeout: Timeout in seconds to wait for a response.
        Returns:
            True if there is a connection, False otherwise.
        """
        try:
            urllib.request.urlopen(test_url, timeout=timeout)
            self.logger.debug("Internet connection is active.")
            return True
        except urllib.error.URLError as e:
            self.logger.error("URLError while checking connection: {e.reason}. Internet connection is missing or blocked.")
        except socket.timeout:
            self.logger.error("Connection check timed out. Internet may be slow or unavailable.")
        except Exception as e:
            self.logger.error(f"Unexpected error while checking connection: {e}")
        return False

    def get_public_ip(self, timeout: int = 5) -> str:
        """Returns the public IP address using an external service.

        Args:
            timeout: Timeout in seconds for a response.
        Returns:
            The public IP address as a string, or empty string if unable to obtain.
        """
        ip_service_urls = [
            "http://icanhazip.com",
            "http://api.ipify.org"
            "http://myexternalip.com/raw"
        ]
        for ip_service_url in ip_service_urls:
            self.logger.debug(f"Trying to get public IP address via {ip_service_url}...")
            try:
                response: http.client.HTTPResponse
                with urllib.request.urlopen(ip_service_url, timeout=timeout) as response:
                    public_ip = response.read().decode('utf-8').strip()
                    self.logger.debug(f"Public IP address: {public_ip}")
                    return public_ip
            except urllib.error.URLError as e:
                self.logger.error(f"URLError when getting public IP: {e.reason}")
                self.logger.error("Unable to obtain public IP address (maybe there is no internet or the service is unavailable).")
            except socket.timeout:
                self.logger.error("Timeout while getting public IP address.")
            except Exception as e:
                self.logger.error(f"Unexpected error while getting public IP address: {e}")
        return ''

    def get_disks_info(self) -> list[dict[str, str]]:
        """Retrieves disk info in human readable format.

        Returns:
            List of dicts with disk info or empty list if error occurs.
            Each dict contains: filesystem, size, used, available, use_percent, mounted_on.
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
            List of discts with process info or empty list if error occurs.
            Each dict contains: user, pid, cpu%, mem%, command, start_time.
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

    def get_throttled_state(self) -> Optional[dict[str, Any]]:
        """
        Gets the throttled status of the Raspberry Pi processor.

        Returns:
            Dict with raw throttled value, bool flags (under_voltage, arm_frequency_capped,
            currently_throttled, soft_temperature_limit, under_voltage_occurred,
            arm_frequency_capped_occurred, throttling_occurred, soft_temperature_limit_occurred)
            and text description.
        """
        command = "vcgencmd get_throttled | cut -d= -f2"
        throttled = self.__get_shell_cmd_output(command).strip('"')
        try:
            throttled_int = int(throttled, 16)
            status = {
                "raw_value": throttled_int,
                "description": "",
                "under_voltage": bool(throttled_int & 0x1),
                "arm_frequency_capped": bool(throttled_int & 0x2),
                "currently_throttled": bool(throttled_int & 0x4),
                "soft_temperature_limit": bool(throttled_int & 0x8),
                "under_voltage_occurred": bool(throttled_int & 0x10000),
                "arm_frequency_capped_occurred": bool(throttled_int & 0x20000),
                "throttling_occurred": bool(throttled_int & 0x40000),
                "soft_temperature_limit_occurred": bool(throttled_int & 0x80000)
            }
            descriptions = []
            if status["under_voltage"]:
                descriptions.append("Undervoltage detected")
            if status["arm_frequency_capped"]:
                descriptions.append("Arm frequency capped")
            if status["currently_throttled"]:
                descriptions.append("Currently throttled")
            if status["soft_temperature_limit"]:
                descriptions.append("Soft temperature limit active")
            if not descriptions:
                descriptions.append("No active issues")
            status["description"] = '; '.join(descriptions)
            return status
        except ValueError as e:
            self.logger.error(f"Error while converting throttled value {throttled} to int: {e}")
        except Exception as e:
            self.logger.error(f"Failed to read throttled status: {e}")
        return None


def main() -> None:
    logger = LoggerSingleton(
        level="INFO",
        colored=True
    ).get_logger()
    pi_info = PiInfo(logger)
    try:
        logger.info(f"Model: {pi_info.model_name}")
        logger.info(f"Revision: {pi_info.revision}")
        logger.info(f"Serial number: {pi_info.serial_number}")
        logger.info(f"Manufacturer: {pi_info.manufacturer}")
        logger.info(f"OS: {pi_info.os_name}")
        throttled_state = pi_info.get_throttled_state()
        if throttled_state:
            logger.info(f"Throttled state: {throttled_state.get('description', 'Unknown')}")
        for interface in ['eth0', 'wlan0']:
            nic_info = pi_info.get_network_interface_info(interface)
            mac_address = nic_info['mac'] or 'Unknown'
            ip_address = nic_info['ip'] or 'Not connected'
            mask = nic_info['mask'] or 'Not connected'
            default_gateway = nic_info['gateway'] or 'Not connected'
            logger.info(f"{interface} interface: MAC address {mac_address}, IP address {ip_address}, Subnet mask: {mask}, Default gateway: {default_gateway}")
        logger.info(f"Wi-Fi network name: {pi_info.get_wifi_network_name()}")
        logger.info(f"Internet connection is{' not' if not pi_info.check_internet_connection() else ''} active")
        logger.info(f"Public IP address: {pi_info.get_public_ip()}")
        while True:
            try:
                cpu_temp = pi_info.get_cpu_temperature()
                cpu_freq = pi_info.get_cpu_core_frequencies()
                cpu_usage = pi_info.get_cpu_usage()
                ram_info = pi_info.get_ram_info()
                logger.info(f"CPU: temperature {cpu_temp} \xb0C, frequency {cpu_freq['cur']} MHz, usage {cpu_usage}%")
                logger.info(f"RAM: total {ram_info['total']} Mb, used {ram_info['used']} Mb, free {ram_info['free']} Mb, "
                            f"cache {ram_info['cache']} Mb, available {ram_info['available']} Mb")
            except Exception as e:
                logger.error(f"Error during system info retrieval: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception in main loop: {e}")


if __name__ == "__main__":
    main()
