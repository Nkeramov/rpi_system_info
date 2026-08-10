import http.client
import logging
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import cached_property
from string import hexdigits
from typing import Any, Literal

from .utils.cls_utils import Singleton
from .utils.log_utils import LoggerSingleton


class ModelType(Enum):
    UNKNOWN = -100

    RPI_A = 0x00
    RPI_B = 0x01
    RPI_A_PLUS = 0x02
    RPI_B_PLUS = 0x03
    RPI_2B = 0x04
    RPI_ALPHA = 0x05
    RPI_CM1 = 0x06
    # 0x07 pass
    RPI_3B = 0x08
    RPI_ZERO = 0x09
    RPI_CM3 = 0x0A
    # 0x0B pass
    RPI_ZERO_W = 0x0C
    RPI_3B_PLUS = 0x0D
    RPI_3A_PLUS = 0x0E
    # 0x0F: Internal use only
    RPI_CM3_PLUS = 0x10
    RPI_4B = 0x11
    RPI_Zero2W = 0x12
    RPI_400 = 0x13
    RPI_CM4 = 0x14
    RPI_CM4S = 0x15
    # 0x16: Internal use only
    RPI_5 = 0x17
    RPI_CM5 = 0x18
    RPI_500_or_500_PLUS = 0x19
    RPI_CM5_LITE = 0x1A
    RPI_CM0 = 0x1B


class IncorrectFrequencyUnitError(Exception):
    """Raise when frequency unit not in ['Hz', 'KHz', 'MHz', 'GHz']"""


@dataclass(frozen=True)
class RPiSystemInfo(metaclass=Singleton):
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
        """Initialize Raspberry Pi hardware information.

        Raises:
            ValueError: if revision code is invalid
            RuntimeError: if hardware info cannot be decoded
        """
        self.logger.debug("Fetching board revision code...")
        command = "cat /proc/cpuinfo | grep 'Revision' | cut -d: -f2"
        fetched_revision_code = self.__get_shell_cmd_output(command)
        self.logger.debug(f"Board revision code: {fetched_revision_code}")
        object.__setattr__(self, 'revision_code', fetched_revision_code)
        try:
            decoded_data = RPiSystemInfo.decode_revision_code(fetched_revision_code)
            self.logger.debug(f"Successfully decoded revision code: {fetched_revision_code}")
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
            self.logger.info("RPiSystemInfo info fully initialized")
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid revision code '{fetched_revision_code}': {e}")
            raise ValueError(f"Cannot initialize with revision code '{fetched_revision_code}': {e}") from e
        except Exception as e:
            self.logger.exception("Failed to initialize RPiSystemInfo")
            raise RuntimeError(f"RPiSystemInfo initialization failed: {e}") from e

    def __str__(self) -> str:
        return (f"Model type: {self.model_type.name}, "
                f"Model name: {self.model_name}, "
                f"Revision: {self.revision}, "
                f"Serial number: {self.serial_number}, "
                f"Manufacturer: {self.manufacturer}, "
                f"CPU model: {self.cpu_model}, "
                f"Memory size: {self.memory_size}Mb")

    @staticmethod
    def decode_revision_code(revision_code: str) -> dict[str, Any]:
        """Decode Raspberry Pi revision code into hardware information.

        Parses hexadecimal revision code and extracts model type, revision,
        memory size, CPU model, manufacturer, and other hardware details.
        Supports both old and new style revision codes.

        Args:
            revision_code: Hexadecimal string representing the revision code

        Returns:
            Dictionary containing decoded hardware information

        Raises:
            ValueError: If revision code is invalid or cannot be decoded
            TypeError: If revision code is not a string
        """
        if not revision_code:
            raise ValueError("Revision code cannot be empty or None")
        if not isinstance(revision_code, str):
            raise TypeError(f"Revision code must be a string, got {type(revision_code).__name__}")
        if not revision_code.startswith(('0x', '0X')) and not all(c in hexdigits for c in revision_code):
            raise ValueError(f"Invalid revision code format: '{revision_code}'. Expected hex string")

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
            0x0015: (ModelType.RPI_A_PLUS, "1.1", 512, "BCM2835", "EMBEST"),
        }
        memory_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384]
        cpu_models = ["BCM2835", "BCM2836", "BCM2837", "BCM2711", "BCM2712"]
        manufacturers = ["Sony UK", "Egoman", "Embest", "Sony Japan", "Embest", "Stadium"]

        try:
            code = int(revision_code, 16)
        except ValueError as e:
            raise ValueError(f"Failed to parse revision code '{revision_code}' as hex: {e}") from e

        flag = (code & 0x800000) >> 23

        try:
            if flag:
                # New style revision code decoding
                memory_index = (code & 0x700000) >> 20
                cpu_index = (code & 0xF000) >> 12
                manufacturer_index = (code & 0xF0000) >> 16
                if memory_index >= len(memory_sizes):
                    raise ValueError(f"Invalid memory size index: {memory_index}")
                if cpu_index >= len(cpu_models):
                    raise ValueError(f"Invalid CPU model index: {cpu_index}")
                if manufacturer_index >= len(manufacturers):
                    raise ValueError(f"Invalid manufacturer index: {manufacturer_index}")
                return {
                    'model_type': ModelType((code & 0xFF0) >> 4),
                    'revision': f"1.{code & 0xF}",
                    'memory_size': memory_sizes[memory_index],
                    'cpu_model': cpu_models[cpu_index],
                    'manufacturer': manufacturers[manufacturer_index],
                    'overvoltage_allowed': bool((code & 0x80000000) >> 31),
                    'otp_programming_allowed': bool((code & 0x40000000) >> 30),
                    'otp_reading_allowed': bool((code & 0x20000000) >> 29),
                }
            else:
                # Old style revision code decoding
                if code not in old_boards_revisions_decoder:
                    raise ValueError(f"Unknown old board revision code: 0x{code:04X}")
                board_data = old_boards_revisions_decoder[code]
                return {
                    'model_type': board_data[0],
                    'revision': board_data[1],
                    'memory_size': board_data[2],
                    'cpu_model': board_data[3],
                    'manufacturer': board_data[4],
                }
        except (IndexError, ValueError) as e:
            raise ValueError(f"Failed to decode revision code 0x{code:08X}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error while decoding revision code: {e}") from e


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
        return RPiSystemInfo.float_to_int_if_zero_fraction(result)

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
            command executes successfully or empty string if the command fails.
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
            The board model name, or empty string if the command fails or the file is not found.
        """
        command = "cat /sys/firmware/devicetree/base/model"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def serial_number(self) -> str:
        """Retrieves the board serial number from /proc/cpuinfo.

        Returns:
            The board serial number, or empty string if the command fails.
        """
        command = "cat /proc/cpuinfo | grep 'Serial' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_architecture(self) -> str:
        """Retrieves the CPU architecture using the 'lscpu' command.

        Returns:
            The CPU architecture, or empty string if the command fails.
        """
        command = "lscpu | grep 'Architecture' | cut -d: -f2"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def cpu_cores_count(self) -> int:
        """Retrieves the number of CPU cores using the 'nproc' command.

        Returns:
            The number of CPU cores, or 0 if the command fails.
        """
        command = "nproc"
        result = self.__get_shell_cmd_output(command)
        try:
            return int(result)
        except ValueError:
            self.logger.error(f"Error while converting number of cores value '{result}' to int")
        return 0

    @cached_property
    def cpu_cache_sizes(self) -> dict[str, str]:
        """Retrieves CPU cache sizes using the 'lscpu' command.

        Returns:
            A dictionary {L1d: size, L1i: size, L2: size}, where size is a string
            representing value in KiB, or empty string if command fails.
        """
        command = "lscpu"
        output = self.__get_shell_cmd_output(command)
        cache_types = ["L1d", "L1i", "L2"]
        cache_sizes = dict.fromkeys(cache_types, "")
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
            The hostname, or empty string if the command fails.
        """
        command = "hostname"
        return self.__get_shell_cmd_output(command)

    @cached_property
    def os_name(self) -> str:
        """Retrieves the pretty OS name from /etc/*-release.

        Returns:
            The pretty OS name, or empty string if the command fails. Removes surrounding quotes.
        """
        command = "cat /etc/*-release | grep PRETTY_NAME | cut -d= -f2"
        return self.__get_shell_cmd_output(command).strip('"')

    @cached_property
    def boot_time(self) -> datetime | None:
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

    def get_cpu_core_voltage(self) -> float | None:
        """Retrieves the CPU core voltage using the 'vcgencmd' command.

        Returns:
            The CPU core voltage, or None if the command fails.
        """
        command = "vcgencmd measure_volts| cut -d= -f2"
        result = self.__get_shell_cmd_output(command)
        try:
            if result is not None:
                return float(result[:-1])
        except (IndexError, ValueError):
            self.logger.error(f"Error while converting CPU voltage value '{result}' to float")
        return None

    def get_cpu_temperature(self) -> float | None:
        """Retrieves the CPU temperature using the 'vcgencmd' command.

        Returns:
            The CPU temperature, or None if the command fails.
        """
        command = "vcgencmd measure_temp | cut -d= -f2 | cut -d\\' -f1"
        result = self.__get_shell_cmd_output(command)
        try:
            if result is not None:
                return float(result)
        except ValueError:
            self.logger.error(f"Error while converting CPU temperature value '{result}' to float")
        return None

    def get_cpu_core_frequencies(self, unit: FrequencyUnit = 'MHz') -> dict[str, int | float]:
        """Retrieves min, max and current CPU core frequencies in specified units (Hz, KHz, MHz or GHz).
        If for some frequency type the command fails, then 0 will return for it.

        Args:
            unit: The desired unit for the core frequency (Hz, KHz, MHz, GHz). Defaults to 'MHz'.

        Returns:
            Dict with CPU core frequencies values in the specified unit.
        """
        core_frequencies = {
            'min': 0.0,
            'max': 0.0,
            'cur': 0.0,
        }
        for ft in core_frequencies:
            command = f"cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_{ft}_freq"
            result = self.__get_shell_cmd_output(command)
            if result:
                try:
                    frequency = float(result) * 1000
                    core_frequencies[ft] = RPiSystemInfo.convert_frequency(frequency, unit)
                except ValueError:
                    self.logger.error(f"Error while converting CPU frequency value '{result}' to float")
                except Exception as e:
                    self.logger.error(f"CPU frequency processing error: {e}")
        return core_frequencies

    def get_cpu_usage(self) -> str:
        """Retrieves the CPU usage using the 'top' command.

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
        ram_info = dict.fromkeys(ram_fields, "")
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
            The network interface info dict with mac address, ip address, network mask,
            broadcast ip address, default gateway ip address and state.
        """
        nic_fields = ['mac', 'ip', 'mask', 'broadcast', 'gateway', 'state']
        nic_info = dict.fromkeys(nic_fields, "")
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

                    ip_addr_cmd = f"ip -4 addr show {interface}"
                    ip_addr_cmd_output = self.__get_shell_cmd_output(ip_addr_cmd)
                    if ip_addr_cmd_output:
                        nic_info['state'] = 'UP'
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', ip_addr_cmd_output)
                        broadcast_match = re.search(r'brd (\d+\.\d+\.\d+\.\d+)', ip_addr_cmd_output)
                        if not ip_match or not broadcast_match:
                            self.logger.error(f"Failed to parse '{ip_addr_cmd}' command output: {ip_addr_cmd_output}")
                        else:
                            nic_info['ip'] = ip_match.group(1)
                            prefix_len = int(ip_match.group(2))
                            nic_info['broadcast'] = broadcast_match.group(1)
                            mask = (0xffffffff << (32 - prefix_len)) & 0xffffffff
                            mask_bytes = [
                                (mask >> 24) & 0xff,
                                (mask >> 16) & 0xff,
                                (mask >> 8) & 0xff,
                                mask & 0xff,
                            ]
                            nic_info['mask'] = ".".join(map(str, mask_bytes))

                            ip_route_cmd = f"ip route show | grep ^def.*{interface}"
                            ip_route_output = self.__get_shell_cmd_output(ip_route_cmd)
                            gateway_match = re.search(r'^default via (\d+\.\d+\.\d+\.\d+)', ip_route_output)
                            if gateway_match:
                                nic_info['gateway'] = gateway_match.group(1)
                    else:
                        self.logger.error(f"Empty output for command {ip_addr_cmd}")
                        return nic_info
                except Exception as e:
                    self.logger.error(f"Unexpected error while retrieving interface {interface} information: {e}")
            else:
                self.logger.error(f"Incorrect network interface: {interface}")
        except FileNotFoundError:
            self.logger.error(f"Can not load network interface info from {self._NET_PATH}")
        self.logger.debug(f"Network interface {interface} info: {', '.join(f'{k}: {v}' for k, v in nic_info.items())}")
        return nic_info

    def get_bluetooth_interface_info(self, interface: str = 'hci0') -> dict[str, str]:
        """
        Retrieves detailed information about a specific Bluetooth interface.

        Args:
            interface: Bluetooth interface name (default: 'hci0').

        Returns:
            A dictionary with keys: 'mac', 'state', 'name', 'manufacturer'.
            Values are strings; empty if the interface is not found or parsing fails.
        """
        bt_fields = ['mac', 'state', 'name', 'manufacturer']
        bt_info = dict.fromkeys(bt_fields, "")
        command = "hciconfig -a"
        output = self.__get_shell_cmd_output(command)
        if output:
            lines = output.splitlines()
            start_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith(interface + ':'):
                    start_idx = i
                    break
            if start_idx is None:
                self.logger.error(f"Bluetooth interface '{interface}' not found in output")
                return {}
            block_lines = []
            for j in range(start_idx, len(lines)):
                if j > start_idx and lines[j].strip().startswith('hci') and ':' in lines[j]:
                    break
                block_lines.append(lines[j])

            for line in block_lines:
                stripped = line.strip()
                try:
                    if 'BD Address:' in stripped:
                        parts = stripped.split('BD Address:')
                        if len(parts) > 1:
                            mac_addr = parts[1].strip().split()[0]
                            if mac_addr:
                                bt_info['mac'] = mac_addr.upper()
                    elif 'Name:' in stripped:
                        parts = stripped.split('Name:')
                        if len(parts) > 1:
                            name = parts[1].strip().strip("'")
                            if name:
                                bt_info['name'] = name
                    elif 'Manufacturer:' in stripped:
                        parts = stripped.split('Manufacturer:')
                        if len(parts) > 1:
                            manufacturer = parts[1].strip()
                            if manufacturer:
                                bt_info['manufacturer'] = manufacturer
                    elif stripped and ':' not in stripped and not stripped.startswith('hci'):
                        if not bt_info['state']:
                            bt_info['state'] = stripped
                except (IndexError, ValueError, AttributeError) as parse_err:
                    self.logger.warning(f"Failed to parse line '{stripped}': {parse_err}")
        else:
            self.logger.error(f"No output from {command}")
        return bt_info

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
                        'security': " ".join(values[k+3:]),
                    })
                return networks
            except Exception as e:
                self.logger.error(f"Unexpected error while retrieving Wi-Fi networks info: {e}")
        return networks

    def get_wifi_network_name(self) -> str:
        """Retrieves the name of the Wi-Fi network to which the Raspberry Pi is connected.

        Returns:
            The Wi-Fi network name, or empty string if unable to obtain.
        """
        try:
            command = "iwgetid -r"
            output = self.__get_shell_cmd_output(command)
            if output is None:
                return ""
            wifi_name = str(output).strip()
            return wifi_name
        except Exception as e:
            self.logger.error(f"Failed to get Wi-Fi network name: {e}")
        return ""

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
            self.logger.error(f"URLError while checking connection: {e.reason}. " \
                "Internet connection is missing or blocked.")
        except TimeoutError:
            self.logger.error("Connection timeout. Internet may be slow or unavailable.")
        except Exception as e:
            self.logger.error(f"Unexpected error while checking connection: {e}.")
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
            "http://myexternalip.com/raw",
        ]
        public_ip = ''
        for ip_service_url in ip_service_urls:
            self.logger.debug(f"Trying to get public IP address via {ip_service_url}...")
            try:
                response: http.client.HTTPResponse
                with urllib.request.urlopen(ip_service_url, timeout=timeout) as response:
                    public_ip = response.read().decode('utf-8').strip()
                    self.logger.debug(f"Public IP address: {public_ip}")
                    return public_ip
            except urllib.error.URLError as e:
                self.logger.error(f"URLError while getting public IP address: {e.reason}. " \
                    "Maybe there is no Internet or the service is unavailable.")
            except TimeoutError:
                self.logger.error("Timeout while getting public IP address.")
            except Exception as e:
                self.logger.error(f"Unexpected error while getting public IP address: {e}.")
        return public_ip

    def get_disks_info(self) -> list[dict[str, str]]:
        """Retrieves disks info in human-readable format.

        Returns:
            List of dicts with disk info or empty list if error occurs.
            Each dict contains: filesystem, size, used, available, use_percent, mounted_on.
        """
        self.logger.debug("Started get_disks_info")
        headers = ["filesystem", "size", "used", "available", "use_percent", "mounted_on"]
        disks: list[dict[str, str]] = []
        command = "df -h --output=source,size,used,avail,pcent,target | head -n 1; df -h | tail -n +2 | sort -k6"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()[1:]
                if not lines:
                    self.logger.warning("No disks information available")
                    return disks
                for line in lines:
                    values = line.split()
                    values = line.split(maxsplit=5)
                    if len(values) != 6:
                        continue
                    disk_info = dict(zip(headers, values, strict=False))
                    disk_info["use_percent"] = disk_info["use_percent"].replace("%", "")
                    disks.append(disk_info)
                return disks
            except Exception as e:
                self.logger.error(f"Unexpected error getting disks info: {e}")
        return disks

    def get_disks_inodes_info(self) -> list[dict[str, str]]:
        """Retrieves disks inodes info.

        Returns:
            List of dicts with disk inodes info or empty list if error occurs.
            Each dict contains: filesystem, inodes, used, free, use_percent, mounted_on.
        """
        self.logger.debug("Started get_disks_inodes_info")
        headers = ["filesystem", "inodes", "used", "free", "use_percent", "mounted_on"]
        disks: list[dict[str, str]] = []
        command = "df -i | head -n 1; df -i | tail -n +2 | sort -k6"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                lines = output.splitlines()[1:]
                if not lines:
                    self.logger.warning("No disks inodes information available")
                    return disks
                for line in lines:
                    values = line.split()
                    values = line.split(maxsplit=5)
                    if len(values) != 6:
                        continue
                    disk_info = dict(zip(headers, values, strict=False))
                    disk_info["use_percent"] = disk_info["use_percent"].replace("%", "")
                    disks.append(disk_info)
                return disks
            except Exception as e:
                self.logger.error(f"Unexpected error getting disks inodes info: {e}")
        return disks

    def get_sd_card_info(self) -> list[dict[str, str | None]]:
        """
        Retrieve information about SD cards (type 'SD') from the sysfs interface,
        including filesystem types of their partitions.

        The function scans /sys/bus/mmc/devices, reads the 'type' file of each
        device, and for those reporting 'SD' it extracts the following fields:
          - Device
          - Type
          - Name
          - OEM App. Id (OID)
          - Serial Number
          - Manufacturer Id
          - Manufacturer
          - Date of manufacture
          - Log. block size
          - Phys. block size
          - Hardware rev.
          - Firmware rev.
          - CID register
          - CSD register
          - DSR register
          - SCR register
          - OCR register
          - Filesystem (as comma-separated list of unique filesystem types found on partitions)

            If a corresponding sysfs file does not exist, the field is set to None.
            For the Filesystem field, the function locates the associated block device
            (e.g., /dev/mmcblk0), iterates over its partitions, and uses 'blkid' to
            determine their filesystem types. If blkid is unavailable or no partitions
            are found, the field is set to None.

            The manufacturer name is determined based on the device type and manufacturer id.

            Returns:
                List of dicts, each containing the information for one SD card.
                Each dict contains: device, type, name, oemid (OID), serial number, manufacturer id,
                manufacturer, date of manufactured, logical block size, physical block size, hardware
                revision, firmware revision, filesystem and CID, CSD, DSR, SCR, OCR registers values.
            """
        manufacturers_db = {
            ('MMC', '0x000000'): 'SanDisk',
            ('MMC', '0x000002'): 'Kingston, or SanDisk',
            ('MMC', '0x000003'): 'Toshiba',
            ('MMC', '0x000005'): 'Unknown',
            ('MMC', '0x000006'): 'Unknown',
            ('MMC', '0x000011'): 'Toshiba',
            ('MMC', '0x000013'): 'Micron',
            ('MMC', '0x000015'): 'Samsung, SanDisk, or LG',
            ('MMC', '0x000037'): 'KingMax',
            ('MMC', '0x000044'): 'ATP',
            ('MMC', '0x000045'): 'SanDisk Corporation',
            ('MMC', '0x000070'): 'Kingston',
            ('MMC', '0x00002c'): 'Kingston',
            ('MMC', '0x0000fe'): 'Micron',
            ('SD', '0x000001'): 'Panasonic',
            ('SD', '0x000002'): 'Kingston, Toshiba, or Viking',
            ('SD', '0x000003'): 'SanDisk',
            ('SD', '0x000008'): 'Silicon Power',
            ('SD', '0x000018'): 'Infineon',
            ('SD', '0x000027'): 'Phison Electronics Corporation',
            ('SD', '0x000028'): 'Lexar',
            ('SD', '0x000030'): 'SanDisk',
            ('SD', '0x000031'): 'Silicon Power',
            ('SD', '0x000033'): 'STMicroelectronics',
            ('SD', '0x000041'): 'Kingston',
            ('SD', '0x00006f'): 'STMicroelectronics',
            ('SD', '0x000074'): 'Transcend',
            ('SD', '0x000076'): 'Patriot',
            ('SD', '0x000082'): 'Gobe, or Sony',
            ('SD', '0x000089'): 'Unknown',
            ('SD', '0x00001b'): 'Samsung, or Transcend',
            ('SD', '0x00001c'): 'Transcend',
            ('SD', '0x00001d'): 'AData, or Corsair',
            ('SD', '0x00001e'): 'Transcend',
            ('SD', '0x00001f'): 'Kingston',
        }
        sd_cards: list[dict[str, str | None]] = []
        mmc_path = "/sys/bus/mmc/devices"

        try:
            devices = os.listdir(mmc_path)
            for device in devices:
                dev_dir = os.path.join(mmc_path, device)
                type_file = os.path.join(dev_dir, "type")

                try:
                    with open(type_file) as f:
                        mmc_type = f.read().strip()
                except (OSError, UnicodeDecodeError):
                    continue

                if mmc_type != "SD":
                    continue

                info: dict[str, str | None] = {
                    "device": device,
                    "type": mmc_type,
                }
                file_mapping = {
                    "name": "name",
                    "oemid": "oemid",
                    "serial_number": "serial",
                    "manufacturer_id": "manfid",
                    "manufactured_date": "date",
                    "logical_block_size": "erase_size",
                    "physical_block_size": "preferred_erase_size",
                    "hardware_revision": "hwrev",
                    "firmware_revision": "fwrev",
                    "cid_register": "cid",
                    "csd_register": "csd",
                    "dsr_register": "dsr",
                    "scr_register": "scr",
                    "ocr_register": "ocr",
                }

                for field, filename in file_mapping.items():
                    file_path = os.path.join(dev_dir, filename)
                    try:
                        with open(file_path) as f:
                            info[field] = f.read().strip()
                    except (OSError, UnicodeDecodeError):
                        info[field] = None

                key = (info['type'], info['manufacturer_id'])
                info['manufacturer'] = manufacturers_db.get(key)

                fs_info = None
                block_dir = os.path.join(dev_dir, "block")
                try:
                    if os.path.isdir(block_dir):
                        block_devices = os.listdir(block_dir)
                        if block_devices:
                            block_name = block_devices[0]
                            sys_block_path = os.path.join("/sys/block", block_name)
                            if os.path.isdir(sys_block_path):
                                partition_fs = []
                                try:
                                    partitions = os.listdir(sys_block_path)
                                except OSError:
                                    partitions = []
                                for entry in partitions:
                                    if entry.startswith(block_name + "p"):
                                        dev_path = f"/dev/{entry}"
                                        try:
                                            output = subprocess.check_output(
                                                ["blkid", "-s", "TYPE", "-o", "value", dev_path],
                                                stderr=subprocess.DEVNULL,
                                                text=True,
                                            ).strip()
                                            if output:
                                                partition_fs.append(output)
                                        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                                            pass
                                if partition_fs:
                                    unique_fs = sorted(set(partition_fs))
                                    fs_info = ", ".join(unique_fs)
                except OSError:
                    pass
                info["filesystem"] = fs_info
                sd_cards.append(info)
        except OSError:
            pass
        return sd_cards

    def get_processes_info(self) -> list[dict[str, Any]]:
        """Retrieves info about running processes in system.

        Returns:
            List of dicts with process info or empty list if error occurs.
            Each dict contains: user, pid, cpu%, mem%, command, start_time.
        """
        self.logger.debug("Started get_processes_info")
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
                            'started_on': datetime.strptime(" ".join(parts[-5:]), "%a %b %d %H:%M:%S %Y"),
                        }
                        if process_info['command'] != 'ps':
                            processes.append(process_info)
                    except (ValueError, IndexError) as parse_error:
                        self.logger.warning(f"Skipping malformed process line: {line} ({parse_error})")
                        continue
                return processes
            except Exception as e:
                self.logger.error(f"Unexpected error getting process info: {e}")
        return processes

    def get_tmux_sessions(self) -> list[dict[str, Any]]:
        """
        Retrieves info about active tmux sessions.

        Returns:
            A list of dicts with tmux session info.
            Each dict contains: session name, number of windows in the session, creation datetime.
            Returns an empty list if tmux is not available, no sessions exist, or an error occurs.
        """
        self.logger.debug("Started get_tmux_sessions")
        sessions: list[dict[str, Any]] = []
        command = "tmux ls"
        output = self.__get_shell_cmd_output(command)
        if output:
            try:
                if isinstance(output, bytes):
                    output = output.decode('utf-8')
                else:
                    output = str(output)
                lines = output.splitlines()
                if not lines:
                    self.logger.warning("No tmux sessions found or tmux server not running")
                    return sessions
                date_pattern = r"\(created\s+(.*?)\)"
                for line in lines:
                    try:
                        if ": " not in line:
                            self.logger.warning(f"Skipping malformed line (missing ': '): {line}")
                            continue
                        name_part, rest = line.split(": ", 1)

                        if " windows (" not in rest:
                            self.logger.warning(f"Skipping malformed line (missing 'windows ('): {line}")
                            continue
                        windows_str, _ = rest.split(" windows (", 1)
                        windows = int(windows_str.strip())

                        match = re.search(date_pattern, rest)
                        if not match:
                            self.logger.warning(f"Skipping line (no creation date found): {line}")
                            continue
                        created_str = match.group(1)
                        created_dt = datetime.strptime(created_str, "%a %b %d %H:%M:%S %Y")

                        sessions.append({
                            "name": name_part.strip(),
                            "windows": windows,
                            "created": created_dt
                        })
                    except (ValueError, IndexError) as parse_error:
                        self.logger.warning(f"Skipping malformed line: {line} ({parse_error})")
                        continue
                return sessions
            except Exception as e:
                self.logger.error(f"Unexpected error while parsing tmux sessions: {e}")
        return sessions

    def get_gpu_codecs_info(self, codecs: list[str] | None = None) -> dict[str, bool]:
        """
        Retrieves the enabled/disabled status of GPU hardware codecs on a Raspberry Pi.

        This method executes `vcgencmd codec_enabled` for each specified codec,
        parses the output, and returns a dictionary with boolean values.

        Args:
            codecs: Optional list of codec names to check. If not provided,
                    defaults to ["H264", "MPG2", "WVC1", "MPG4", "MJPG", "WMV9"].

        Returns:
            A dictionary where keys are codec names (as given in the input list)
            and values are True if the codec is enabled, False otherwise.
        """
        if codecs is None:
            codecs = ["H264", "MPG2", "WVC1", "MPG4", "MJPG", "WMV9"]
        status_dict: dict[str, bool] = {}
        for codec in codecs:
            try:
                cmd = f"vcgencmd codec_enabled {codec}"
                output = self.__get_shell_cmd_output(cmd)
                if '=' not in output:
                    self.logger.warning(f"Unexpected output format for codec '{codec}': {output!r}")
                    status_dict[codec] = False
                    continue
                _, status_str = output.split('=', 1)
                status_str = status_str.strip().lower()
                status_dict[codec] = (status_str == "enabled")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to check codec '{codec}' (exit code {e.returncode}): {e.stderr}")
                status_dict[codec] = False
            except Exception as e:
                self.logger.error(f"Unexpected error while checking codec '{codec}': {e}")
                status_dict[codec] = False
        return status_dict

    def get_throttled_state(self) -> dict[str, Any] | None:
        """
        Retrieves the throttled status of the Raspberry Pi processor.

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
                "soft_temperature_limit_occurred": bool(throttled_int & 0x80000),
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
    LoggerSingleton(level="INFO", colored=True)
    logger = LoggerSingleton.get_logger()
    rpi_info = RPiSystemInfo(logger)
    try:
        logger.info(f"Model: {rpi_info.model_name}")
        logger.info(f"Revision: {rpi_info.revision}")
        logger.info(f"Serial number: {rpi_info.serial_number}")
        logger.info(f"Manufacturer: {rpi_info.manufacturer}")
        logger.info(f"OS: {rpi_info.os_name}")
        throttled_state = rpi_info.get_throttled_state()
        if throttled_state:
            logger.info(f"Throttled state: {throttled_state.get('description', 'Unknown')}")
        for interface in ['eth0', 'wlan0']:
            nic_info = rpi_info.get_network_interface_info(interface)
            mac_address = nic_info['mac'] or 'Unknown'
            ip_address = nic_info['ip'] or 'Not connected'
            mask = nic_info['mask'] or 'Not connected'
            default_gateway = nic_info['gateway'] or 'Not connected'
            logger.info(f"{interface} interface: MAC address {mac_address}, IP address {ip_address}, " \
                    f"Subnet mask: {mask}, Default gateway: {default_gateway}")
        wifi_network_name = rpi_info.get_wifi_network_name() or 'Not connected'
        logger.info(f"Wi-Fi network name: {wifi_network_name}")
        if rpi_info.check_internet_connection():
            logger.info(f"Internet connection is active, public IP address: {rpi_info.get_public_ip()}")
        else:
            logger.info("Internet connection is not active")
        while True:
            try:
                cpu_temp = rpi_info.get_cpu_temperature()
                cpu_freq = rpi_info.get_cpu_core_frequencies()
                cpu_usage = rpi_info.get_cpu_usage()
                ram_info = rpi_info.get_ram_info()
                logger.info(f"CPU: temperature {cpu_temp} \xb0C, frequency {cpu_freq['cur']} MHz, usage {cpu_usage}%")
                logger.info(f"RAM: total {ram_info['total']} Mb, used {ram_info['used']} Mb, " \
                        f"free {ram_info['free']} Mb, cache {ram_info['cache']} Mb, " \
                        f"available {ram_info['available']} Mb")
            except Exception as e:
                logger.error(f"Error during system info retrieval: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception in main loop: {e}")


if __name__ == "__main__":
    main()
