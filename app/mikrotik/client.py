"""MikroTik RouterOS API client with multi-device support."""

import logging
import ssl
from contextlib import contextmanager
from typing import Any, Generator

import routeros_api

from ..config import MikroTikDevice, get_config

logger = logging.getLogger(__name__)


class MikroTikClient:
    """Client for interacting with a MikroTik router."""

    def __init__(self, device: MikroTikDevice):
        self.device = device
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with the device's certificate."""
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile=str(self.device.ssl_cert))
        return ctx

    def _create_connection(self) -> routeros_api.RouterOsApiPool:
        """Create a new API connection pool."""
        return routeros_api.RouterOsApiPool(
            host=self.device.host,
            port=self.device.port,
            use_ssl=True,
            ssl_verify=True,
            ssl_verify_hostname=True,
            username=self.device.username,
            password=self.device.password,
            plaintext_login=True,
            ssl_context=self._ssl_context,
        )

    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """Context manager for API connections."""
        connection = self._create_connection()
        try:
            yield connection.get_api()
        finally:
            connection.disconnect()

    # --- System Commands ---

    def get_identity(self) -> str:
        """Get router identity name."""
        with self.connect() as api:
            identity = api.get_resource('/system/identity')
            result = identity.get()
            return result[0].get('name', 'Unknown') if result else 'Unknown'

    def get_system_resource(self) -> dict:
        """Get system resource information (CPU, memory, uptime, version)."""
        with self.connect() as api:
            resource = api.get_resource('/system/resource')
            result = resource.get()
            return result[0] if result else {}

    def get_interfaces(self) -> list[dict]:
        """Get all interfaces with their status."""
        with self.connect() as api:
            interfaces = api.get_resource('/interface')
            return interfaces.get()

    def get_logs(self, limit: int = 20) -> list[dict]:
        """Get recent log entries."""
        with self.connect() as api:
            logs = api.get_resource('/log')
            all_logs = logs.get()
            return all_logs[-limit:] if all_logs else []

    def get_dhcp_leases(self) -> list[dict]:
        """Get DHCP server leases."""
        with self.connect() as api:
            leases = api.get_resource('/ip/dhcp-server/lease')
            return leases.get()

    # --- Update Commands ---

    def check_for_updates(self) -> dict:
        """Check for RouterOS updates."""
        with self.connect() as api:
            package = api.get_resource('/system/package/update')
            package.call('check-for-updates')
            result = package.get()
            return result[0] if result else {}

    def install_updates(self) -> None:
        """Download and install RouterOS updates (will reboot)."""
        with self.connect() as api:
            package = api.get_resource('/system/package/update')
            package.call('install')

    # --- System Control ---

    def reboot(self) -> None:
        """Reboot the router."""
        with self.connect() as api:
            system = api.get_resource('/system')
            system.call('reboot')


def get_client(slug: str) -> MikroTikClient | None:
    """Get a MikroTik client by device slug."""
    config = get_config()
    device = config.get_mikrotik_device(slug)
    if device is None:
        return None
    return MikroTikClient(device)


def get_all_clients() -> list[MikroTikClient]:
    """Get clients for all configured MikroTik devices."""
    config = get_config()
    return [MikroTikClient(device) for device in config.mikrotik_devices]
