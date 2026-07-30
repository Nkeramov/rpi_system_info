from datetime import datetime
from typing import Any

from ..core.utils.helpers import format_datetime


def register(app, rpi_info, config):
    @app.context_processor
    def generic_board_info() -> dict[str, dict[str, Any]]:
        system_time = format_datetime(datetime.now(), config.TEXT_DATETIME_FORMAT)
        boot_time = rpi_info.boot_time
        boot_time_str = format_datetime(boot_time, config.TEXT_DATETIME_FORMAT) if boot_time else ''
        return {
            'generic_board_info': {
                'model_name': rpi_info.model_name,
                'revision': rpi_info.revision,
                'serial_number': rpi_info.serial_number,
                'manufacturer': rpi_info.manufacturer,
                'os': rpi_info.os_name,
                'hostname': rpi_info.hostname,
                'system_time': system_time,
                'boot_time': boot_time_str,
                'uptime_pretty': rpi_info.get_uptime_pretty(),
                'internet_connection_status': rpi_info.check_internet_connection(),
                'public_ip': rpi_info.get_public_ip(),
            },
        }

    @app.context_processor
    def cpu_details() -> dict[str, dict[str, Any]]:
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
                'core_voltage': f"{voltage: .3f}" if voltage is not None else None,
                'cache_sizes': rpi_info.cpu_cache_sizes,
                'usage': rpi_info.get_cpu_usage(),
                'temperature_value': temperature,
                'temperature_color': color,
                'overvoltage_allowed': 'Yes' if rpi_info.overvoltage_allowed else 'No',
                'otp_programming_allowed': 'Yes' if rpi_info.otp_programming_allowed else 'No',
                'otp_reading_allowed': 'Yes' if rpi_info.otp_reading_allowed else 'No',
            },
        }

    @app.context_processor
    def ram_details() -> dict[str, dict[str, str]]:
        return {
            'ram_details': rpi_info.get_ram_info(),
        }

    @app.context_processor
    def eth_interface_info() -> dict[str, dict[str, str]]:
        return {
            'eth_info': rpi_info.get_network_interface_info('eth0'),
        }

    @app.context_processor
    def wlan_interface_info() -> dict[str, dict[str, str]]:
        return {
            'wlan_info': rpi_info.get_network_interface_info('wlan0'),
        }

    @app.context_processor
    def wifi_network_name() -> dict[str, str]:
        network_name = rpi_info.get_wifi_network_name()
        return {
            'wifi_network_name': network_name,
        }

    @app.context_processor
    def bluetooth_mac_address() -> dict[str, str]:
        address = rpi_info.get_bluetooth_mac_address()
        return {
            'bluetooth_mac_address': address,
        }

    @app.context_processor
    def available_wifi_networks() -> dict[str, list[dict[str, str]]]:
        return {
            'available_wifi_networks': rpi_info.get_available_wifi_networks(),
        }

    @app.context_processor
    def disks_details() -> dict[str, list[dict[str, str]]]:
        return {
            'disks_details': rpi_info.get_disks_info(),
        }

    @app.context_processor
    def disks_inodes_details() -> dict[str, list[dict[str, str]]]:
        return {
            'disks_inodes_details': rpi_info.get_disks_inodes_info(),
        }

    @app.context_processor
    def processes_details() -> dict[str, list[dict[str, Any]]]:
        processes_details = rpi_info.get_processes_info()
        for process in processes_details:
            if process.get('started_on'):
                process['started_on'] = format_datetime(process['started_on'], config.TEXT_DATETIME_FORMAT)
        return {
            'processes_details': processes_details,
        }

    @app.context_processor
    def sd_card_details() -> dict[str, dict[str, str | None]]:
        sd_info = rpi_info.get_sd_card_info()
        first = sd_info[0] if sd_info else {}
        return {
            'sd_card_details': first,
        }
