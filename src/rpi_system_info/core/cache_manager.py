import threading
import time
from logging import Logger
from typing import Any, Callable

from .data_providers import get_hardware_data, get_network_data, get_storage_data, get_processes_data


class CacheManager:
    def __init__(
        self,
        rpi_info,
        config,
        logger: Logger,
        background_updates: bool = True
    ):
        """
        rpi_info: An instance of RPiSystemInfo containing all system data.
        config: Application configuration object with thresholds and formatting.
        update_interval: background update interval (seconds) if background_updates=True.
        ttl_seconds: maximum data age (seconds) after which it is forced to update when requested.
        background_updates: whether to run a background thread for periodic updates.
        """
        self.rpi_info = rpi_info
        self.config = config
        self.logger = logger

        self.update_interval = getattr(config, 'METRICS_UPDATE_INTERVAL', 15)
        self.ttl = getattr(config, 'METRICS_TTL', 30)
        self.background_updates = background_updates

        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

        self._stop_event = threading.Event()

        self._providers = {
            'hardware': (get_hardware_data, (self.rpi_info, self.config), {}),
            'network': (get_network_data, (self.rpi_info,), {}),
            'storage': (get_storage_data, (self.rpi_info,), {}),
            'processes': (get_processes_data, (self.rpi_info, self.config), {}),
        }

        self._update_all()

        if self.background_updates:
            self._thread = threading.Thread(target=self._updater_loop, daemon=True)
            self._thread.start()
        else:
            self._thread = None

        self.logger.info(
            f"CacheManager initialized with update_interval={self.update_interval}s, "
            f"TTL={self.ttl}s, background_updates={self.background_updates}, "
            f"providers={list(self._providers.keys())}"
        )

    def _update_all(self):
        """Calls all providers and updates the cache."""
        timestamps = {}
        with self._lock:
            for key in self._providers.keys():
                entry = self._cache.get(key)
                timestamps[key] = entry['timestamp'] if entry and 'timestamp' in entry else 0.0
        sorted_keys = sorted(timestamps.keys(), key=lambda k: timestamps[k])

        for key in sorted_keys:
            func, args, kwargs = self._providers[key]
            try:
                data = func(*args, **kwargs)
                with self._lock:
                    self._cache[key] = {
                        'data': data,
                        'timestamp': time.time()
                    }
                self.logger.debug(f"Successfully updated in the background: {key}")
            except Exception as e:
                self.logger.error(f"Failed to update {key}: {e}")

    def _updater_loop(self):
        """Background update loop."""
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.update_interval):
                break
            self._update_all()

    def _get_or_refresh(self, key: str) -> Any:
        """
        Returns the data for the key, synchronously updating it if necessary,
        if it is missing or older than the TTL.
        """
        with self._lock:
            entry = self._cache.get(key)
            now = time.time()
            if entry and (now - entry['timestamp']) <= self.ttl:
                return entry['data']

        if key not in self._providers:
            raise KeyError(f"Unknown provider key: {key}")

        func, args, kwargs = self._providers[key]
        try:
            new_data = func(*args, **kwargs)
            with self._lock:
                self._cache[key] = {
                    'data': new_data,
                    'timestamp': time.time()
                }
            self.logger.debug(f"Sync refresh: {key}")
            return new_data
        except Exception as e:
            self.logger.error(f"Failed to refresh {key}: {e}")
            with self._lock:
                entry = self._cache.get(key)
                return entry['data'] if entry else {}

    def get_hardware(self) -> dict:
        return self._get_or_refresh('hardware')

    def get_storage(self) -> dict:
        return self._get_or_refresh('storage')

    def get_network(self) -> dict:
        return self._get_or_refresh('network')

    def get_processes(self) -> dict:
        return self._get_or_refresh('processes')

    def get(self, key: str) -> Any:
        return self._get_or_refresh(key)

    def get_timestamp(self, key: str) -> float | None:
        with self._lock:
            entry = self._cache.get(key)
            return entry['timestamp'] if entry else None

    def force_refresh(self):
        """Forced synchronous update of all data."""
        self._update_all()

    def force_refresh_by_key(self, key: str):
        """Forced update of one key."""
        if key not in self._providers:
            raise ValueError(f"Unknown provider key: {key}")
        func, args, kwargs = self._providers[key]
        try:
            data = func(*args, **kwargs)
            with self._lock:
                self._cache[key] = {
                    'data': data,
                    'timestamp': time.time()
                }
            self.logger.info(f"Successfully force refresh of {key}")
        except Exception as e:
            self.logger.error(f"Failed to refresh {key}: {e}")
            raise

    def stop(self):
        """Stops the background thread, if one is running."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2)
