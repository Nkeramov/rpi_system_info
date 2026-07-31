"""
Data provider functions for system information.

Each function returns a dictionary that can be directly unpacked into a template
context. They are used by the dynamic partial endpoints.
"""

from datetime import datetime
from typing import Any

from ..config import AppConfig
from .system_info import RPiSystemInfo
from .utils.helpers import format_datetime


def get_generic_data(rpi_info: RPiSystemInfo, config: AppConfig) -> dict[str, dict[str, Any]]:
    """
    Return all data needed for the "Generic" tab.

    This combines board information, CPU details, and RAM details into one
    dictionary that can be passed to the `partials/generic.html` template.

    Args:
        rpi_info: An instance of RPiSystemInfo containing all system data.
        config: Application configuration object with thresholds and formatting.

    Returns:
        A dictionary with three top-level keys:
            - 'generic_board_info': dict with board model, revision, serial,
              manufacturer, OS, hostname, system time, boot time, uptime,
              internet connectivity status, and public IP.
            - 'cpu_details': dict as returned by get_cpu_data().
            - 'ram_details': dict as returned by get_ram_data().
    """
    system_time = datetime.now()
    system_time_str = format_datetime(system_time, config.TEXT_DATETIME_FORMAT)
    boot_time = rpi_info.boot_time
    boot_time_str = format_datetime(boot_time, config.TEXT_DATETIME_FORMAT) if boot_time else ''

    generic = {
        'model_name': rpi_info.model_name,
        'revision': rpi_info.revision,
        'serial_number': rpi_info.serial_number,
        'manufacturer': rpi_info.manufacturer,
        'os': rpi_info.os_name,
        'hostname': rpi_info.hostname,
        'system_time': system_time_str,
        'boot_time': boot_time_str,
        'uptime_pretty': rpi_info.get_uptime_pretty(),
        'internet_connection_status': rpi_info.check_internet_connection(),
        'public_ip': rpi_info.get_public_ip(),
    }

    cpu = get_cpu_data(rpi_info, config)
    ram = get_ram_data(rpi_info)

    return {
        'generic_board_info': generic,
        'cpu_details': cpu['cpu_details'],
        'ram_details': ram['ram_details'],
    }


def get_cpu_data(rpi_info: RPiSystemInfo, config: AppConfig) -> dict[str, dict[str, Any]]:
    """
    Collect and format CPU-related metrics.

    This includes model, architecture, core count, frequencies, voltage,
    cache sizes, usage percentage, temperature (with appropriate colour code),
    and various hardware capability flags.

    Args:
        rpi_info: An instance of RPiSystemInfo.
        config: Application configuration (provides temperature thresholds
                and colour constants).

    Returns:
        A dictionary with a single key 'cpu_details' containing a nested dict
        with the following fields:
            - model (str): CPU model name.
            - architecture (str): CPU architecture (e.g., 'armv7l').
            - cores_count (int): Number of CPU cores.
            - min_core_frequency (int or None): Minimum core frequency in MHz.
            - cur_core_frequency (int or None): Current core frequency in MHz.
            - max_core_frequency (int or None): Maximum core frequency in MHz.
            - core_voltage (str or None): Core voltage formatted with 3 decimals.
            - cache_sizes (dict): L1d, L1i, L2 cache sizes in KiB.
            - usage (float): CPU usage percentage.
            - temperature_value (float or None): CPU temperature in °C.
            - temperature_color (str): CSS colour code based on temperature
              thresholds (green/orange/red).
            - overvoltage_allowed (str): 'Yes' or 'No'.
            - otp_programming_allowed (str): 'Yes' or 'No'.
            - otp_reading_allowed (str): 'Yes' or 'No'.
    """
    temperature = rpi_info.get_cpu_temperature()
    color = config.TEXT_GREEN_COLOR
    if temperature is not None:
        if config.CPU_ORANGE_TEMP_THRESHOLD < temperature < config.CPU_RED_TEMP_THRESHOLD:
            color = config.TEXT_ORANGE_COLOR
        elif temperature >= config.CPU_RED_TEMP_THRESHOLD:
            color = config.TEXT_RED_COLOR

    voltage = rpi_info.get_cpu_core_voltage()
    freqs = rpi_info.get_cpu_core_frequencies()

    return {
        'cpu_details': {
            'model': rpi_info.cpu_model,
            'architecture': rpi_info.cpu_architecture,
            'cores_count': rpi_info.cpu_cores_count,
            'min_core_frequency': freqs.get('min'),
            'cur_core_frequency': freqs.get('cur'),
            'max_core_frequency': freqs.get('max'),
            'core_voltage': f"{voltage:.3f}" if voltage is not None else None,
            'cache_sizes': rpi_info.cpu_cache_sizes,
            'usage': rpi_info.get_cpu_usage(),
            'temperature_value': temperature,
            'temperature_color': color,
            'overvoltage_allowed': 'Yes' if rpi_info.overvoltage_allowed else 'No',
            'otp_programming_allowed': 'Yes' if rpi_info.otp_programming_allowed else 'No',
            'otp_reading_allowed': 'Yes' if rpi_info.otp_reading_allowed else 'No',
        }
    }


def get_ram_data(rpi_info: RPiSystemInfo) -> dict[str, dict[str, str]]:
    """
    Retrieve current RAM usage information.

    Args:
        rpi_info: An instance of RPiSystemInfo.

    Returns:
        A dictionary with a single key 'ram_details' containing:
            - total (str): Total RAM in MB.
            - used (str): Used RAM in MB.
            - free (str): Free RAM in MB.
            - percent (str): Used percentage (as a string).
    """
    return {
        'ram_details': rpi_info.get_ram_info()
    }


def get_network_data(rpi_info: RPiSystemInfo) -> dict[str, Any]:
    """
    Collect network interface and Wi‑Fi related information.

    This includes Ethernet and Wi‑Fi interface details, the current SSID,
    Bluetooth MAC address, and a list of available Wi‑Fi networks with signal
    strengths.

    Args:
        rpi_info: An instance of RPiSystemInfo.

    Returns:
        A dictionary with the following keys:
            - eth_info (dict): MAC and IP for eth0.
            - wlan_info (dict): MAC and IP for wlan0.
            - wifi_network_name (str or None): Currently connected SSID.
            - bluetooth_mac_address (str or None): Bluetooth adapter MAC.
            - available_wifi_networks (list[dict]): List of networks, each with
              'ssid' and 'signal' keys.
    """
    return {
        'eth_info': rpi_info.get_network_interface_info('eth0'),
        'wlan_info': rpi_info.get_network_interface_info('wlan0'),
        'wifi_network_name': rpi_info.get_wifi_network_name(),
        'bluetooth_mac_address': rpi_info.get_bluetooth_mac_address(),
        'available_wifi_networks': rpi_info.get_available_wifi_networks(),
    }


def get_storage_data(rpi_info: RPiSystemInfo) -> dict[str, Any]:
    """
    Retrieve storage (disk) usage and inode information.

    Args:
        rpi_info: An instance of RPiSystemInfo.

    Returns:
        A dictionary with three keys:
            - disks_details (list[dict]): List of mounted filesystems with
              total, used, free (in GB) and usage percentage.
            - disks_inodes_details (list[dict]): Inode usage for each mount.
            - sd_card_details (dict or None): SD card health/status info.
    """
    sd_info = rpi_info.get_sd_card_info()
    first = sd_info[0] if sd_info else {}
    return {
        'disks_details': rpi_info.get_disks_info(),
        'disks_inodes_details': rpi_info.get_disks_inodes_info(),
        'sd_card_details': first,
    }


def get_processes_data(rpi_info: RPiSystemInfo, config: AppConfig) -> dict[str, list[dict[str, Any]]]:
    """
    Retrieve a list of running processes with formatted start times.

    The start time of each process is converted to a string using the
    application's configured datetime format.

    Args:
        rpi_info: An instance of RPiSystemInfo.
        config: Application configuration (provides datetime format string).

    Returns:
        A dictionary with a single key 'processes_details' containing a list of
        process dictionaries. Each process dict includes:
            - user (str)
            - pid (int)
            - cpu_percent (float)
            - memory_percent (float)
            - command (str)
            - started_on (str): formatted start time.
    """
    processes = rpi_info.get_processes_info()
    for p in processes:
        if p.get('started_on'):
            p['started_on'] = format_datetime(p['started_on'], config.TEXT_DATETIME_FORMAT)
    return {
        'processes_details': processes
    }
