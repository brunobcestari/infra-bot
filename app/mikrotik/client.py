"""MikroTik RouterOS API client with multi-device support."""

import ssl
from contextlib import contextmanager
from typing import Any, Generator

import routeros_api

from ..config import MikroTikDevice, get_config
from .._internal import get_logger

logger = get_logger(__name__)


class MikroTikClient:
    """Client for interacting with a MikroTik router."""

    def __init__(self, device: MikroTikDevice):
        self.device = device
        self._ssl_context = self._create_ssl_context()
        logger.debug(f"Initialized client for device '{device.name}' ({device.host}:{device.port})")

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with the device's certificate."""
        logger.debug(f"Creating SSL context with cert: {self.device.ssl_cert}")
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile=str(self.device.ssl_cert))
        return ctx

    def _create_connection(self) -> routeros_api.RouterOsApiPool:
        """Create a new API connection pool."""
        logger.debug(f"Creating connection to {self.device.host}:{self.device.port}")
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
        logger.debug(f"Connecting to {self.device.name}")
        connection = self._create_connection()
        try:
            yield connection.get_api()
            logger.debug(f"Connection to {self.device.name} successful")
        finally:
            connection.disconnect()
            logger.debug(f"Disconnected from {self.device.name}")

    # --- System Commands ---

    def get_identity(self) -> str:
        """Get router identity name."""
        logger.debug(f"Getting identity for {self.device.name}")
        with self.connect() as api:
            identity = api.get_resource('/system/identity')
            result = identity.get()
            name = result[0].get('name', 'Unknown') if result else 'Unknown'
            logger.debug(f"Identity for {self.device.name}: {name}")
            return name

    def get_system_resource(self) -> dict:
        """Get system resource information (CPU, memory, uptime, version)."""
        logger.debug(f"Getting system resources for {self.device.name}")
        with self.connect() as api:
            resource = api.get_resource('/system/resource')
            result = resource.get()
            return result[0] if result else {}

    def get_interfaces(self) -> list[dict]:
        """Get all interfaces with their status."""
        logger.debug(f"Getting interfaces for {self.device.name}")
        with self.connect() as api:
            interfaces = api.get_resource('/interface')
            result = interfaces.get()
            logger.debug(f"Found {len(result)} interfaces on {self.device.name}")
            return result

    def get_logs(self, limit: int = 20) -> list[dict]:
        """Get recent log entries."""
        logger.debug(f"Getting last {limit} logs for {self.device.name}")
        with self.connect() as api:
            logs = api.get_resource('/log')
            all_logs = logs.get()
            return all_logs[-limit:] if all_logs else []

    def get_dhcp_leases(self) -> list[dict]:
        """Get DHCP server leases."""
        logger.debug(f"Getting DHCP leases for {self.device.name}")
        with self.connect() as api:
            leases = api.get_resource('/ip/dhcp-server/lease')
            result = leases.get()
            logger.debug(f"Found {len(result)} DHCP leases on {self.device.name}")
            return result
        
    def get_services_all(self) -> list[dict]:
        """Get all IP services on the router."""
        logger.debug(f"Getting all services for {self.device.name}")
        with self.connect() as api:
            services = api.get_resource('/ip/service')
            return services.get()
        
    def get_services_enabled(self) -> list[dict]:
        """Get enabled services on the router."""
        logger.debug(f"Getting enabled services for {self.device.name}")
        with self.connect() as api:
            services_enabled = api.get_resource('/ip/service').get(disabled='no', dynamic='no')
            logger.debug(f"Found {len(services_enabled)} enabled services on {self.device.name}")
            return services_enabled
            
    # --- Update Commands ---

    def check_for_updates(self) -> dict:
        """Check for RouterOS updates."""
        logger.info(f"Checking for updates on {self.device.name}")
        with self.connect() as api:
            package = api.get_resource('/system/package/update')
            package.call('check-for-updates')
            result = package.get()
            update_info = result[0] if result else {}
            if update_info:
                logger.info(f"Update check for {self.device.name}: installed={update_info.get('installed-version')}, latest={update_info.get('latest-version')}")
            return update_info

    def install_updates(self) -> None:
        """Download and install RouterOS updates (will reboot)."""
        logger.warning(f"Installing updates on {self.device.name} - device will reboot")
        with self.connect() as api:
            package = api.get_resource('/system/package/update')
            package.call('install')
            logger.info(f"Update install command sent to {self.device.name}")

    # --- System Control ---

    def reboot(self) -> None:
        """Reboot the router."""
        logger.warning(f"Rebooting {self.device.name}")
        with self.connect() as api:
            system = api.get_resource('/system')
            system.call('reboot')
            logger.info(f"Reboot command sent to {self.device.name}")


def get_client(slug: str) -> MikroTikClient | None:
    """Get a MikroTik client by device slug."""
    logger.debug(f"Getting client for slug: {slug}")
    config = get_config()
    device = config.get_mikrotik_device(slug)
    if device is None:
        logger.warning(f"Device not found for slug: {slug}")
        return None
    return MikroTikClient(device)


def get_all_clients() -> list[MikroTikClient]:
    """Get clients for all configured MikroTik devices."""
    config = get_config()
    clients = [MikroTikClient(device) for device in config.mikrotik_devices]
    logger.debug(f"Created {len(clients)} MikroTik clients")
    return clients
