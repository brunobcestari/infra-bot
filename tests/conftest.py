"""Shared test fixtures and configuration."""

import json
import os
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Config, MikroTikDevice


# --- Environment Fixtures ---

@pytest.fixture
def mock_env(tmp_path: Path) -> Generator[dict[str, str], None, None]:
    """Provide clean environment variables for testing."""
    env_vars = {
        "TELEGRAM_BOT_TOKEN": "test-token-123",
        "MIKROTIK_MAIN_ROUTER_PASSWORD": "test-password-main",
        "MIKROTIK_OFFICE_PASSWORD": "test-password-office",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def sample_config_data() -> dict[str, Any]:
    """Sample configuration data."""
    return {
        "telegram": {
            "admin_ids": [123456789, 987654321]
        },
        "devices": {
            "mikrotik": [
                {
                    "name": "Main Router",
                    "host": "192.168.88.1",
                    "port": 8729,
                    "username": "admin",
                    "ssl_cert": "mikrotik/certs/main_router.crt"
                },
                {
                    "name": "Office",
                    "host": "192.168.1.1",
                    "port": 8729,
                    "username": "admin",
                    "ssl_cert": "mikrotik/certs/office.crt"
                }
            ]
        }
    }


@pytest.fixture
def config_file(tmp_path: Path, sample_config_data: dict) -> Path:
    """Create a temporary config file."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(sample_config_data))
    return config_path


@pytest.fixture
def ssl_certs(tmp_path: Path) -> Path:
    """Create temporary SSL certificate files."""
    certs_dir = tmp_path / "app" / "mikrotik" / "certs"
    certs_dir.mkdir(parents=True)

    # Create dummy cert files
    (certs_dir / "main_router.crt").write_text("DUMMY CERT")
    (certs_dir / "office.crt").write_text("DUMMY CERT")

    return certs_dir


# --- Config Fixtures ---

@pytest.fixture
def sample_mikrotik_device(tmp_path: Path) -> MikroTikDevice:
    """Create a sample MikroTik device for testing.

    Note: SSL context is mocked in tests, so cert content doesn't matter.
    """
    cert_path = tmp_path / "test.crt"
    cert_path.touch()  # Empty file - SSL is mocked

    return MikroTikDevice(
        name="Test Router",
        slug="test_router",
        host="192.168.1.1",
        port=8729,
        username="admin",
        password="test-password",
        ssl_cert=cert_path,
    )


@pytest.fixture
def sample_config(sample_mikrotik_device: MikroTikDevice) -> Config:
    """Create a sample config for testing."""
    return Config(
        telegram_token="test-token",
        admin_ids=frozenset([123456789]),
        mikrotik_devices=(sample_mikrotik_device,),
    )


# --- Telegram Fixtures ---

@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock Telegram user."""
    user = MagicMock()
    user.id = 123456789
    user.first_name = "Test"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_unauthorized_user() -> MagicMock:
    """Create a mock unauthorized Telegram user."""
    user = MagicMock()
    user.id = 999999999
    user.first_name = "Unauthorized"
    user.username = "baduser"
    return user


@pytest.fixture
def mock_message() -> AsyncMock:
    """Create a mock Telegram message."""
    message = AsyncMock()
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_user: MagicMock, mock_message: AsyncMock) -> MagicMock:
    """Create a mock Telegram update."""
    update = MagicMock()
    update.effective_user = mock_user
    update.message = mock_message
    update.effective_message = mock_message
    return update


@pytest.fixture
def mock_update_unauthorized(mock_unauthorized_user: MagicMock, mock_message: AsyncMock) -> MagicMock:
    """Create a mock Telegram update from unauthorized user."""
    update = MagicMock()
    update.effective_user = mock_unauthorized_user
    update.message = mock_message
    update.effective_message = mock_message
    return update


@pytest.fixture
def mock_update_no_user(mock_message: AsyncMock) -> MagicMock:
    """Create a mock Telegram update with no user."""
    update = MagicMock()
    update.effective_user = None
    update.message = mock_message
    update.effective_message = mock_message
    return update


@pytest.fixture
def mock_callback_query() -> AsyncMock:
    """Create a mock callback query."""
    query = AsyncMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "mt:status:test_router"
    return query


@pytest.fixture
def mock_update_callback(mock_user: MagicMock, mock_callback_query: AsyncMock) -> MagicMock:
    """Create a mock Telegram update with callback query."""
    update = MagicMock()
    update.effective_user = mock_user
    update.callback_query = mock_callback_query
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock Telegram context."""
    context = MagicMock()
    context.args = []
    return context


# --- MikroTik API Fixtures ---

@pytest.fixture
def mock_mikrotik_api() -> MagicMock:
    """Create a mock MikroTik API."""
    api = MagicMock()

    # Mock resources
    identity_resource = MagicMock()
    identity_resource.get.return_value = [{"name": "TestRouter"}]

    system_resource = MagicMock()
    system_resource.get.return_value = [{
        "cpu-load": "5",
        "free-memory": "500000000",
        "total-memory": "1000000000",
        "free-hdd-space": "100000000",
        "total-hdd-space": "500000000",
        "uptime": "1d2h3m4s",
        "board-name": "RB4011",
        "version": "7.10",
        "architecture-name": "arm64",
    }]

    interface_resource = MagicMock()
    interface_resource.get.return_value = [
        {
            "name": "ether1",
            "type": "ether",
            "running": "true",
            "disabled": "false",
            "tx-byte": "1000000",
            "rx-byte": "2000000",
        },
        {
            "name": "wlan1",
            "type": "wlan",
            "running": "false",
            "disabled": "true",
            "tx-byte": "0",
            "rx-byte": "0",
        },
    ]

    log_resource = MagicMock()
    log_resource.get.return_value = [
        {"time": "12:00:00", "topics": "system", "message": "Test log 1"},
        {"time": "12:01:00", "topics": "interface", "message": "Test log 2"},
    ]

    dhcp_resource = MagicMock()
    dhcp_resource.get.return_value = [
        {"host-name": "device1", "address": "192.168.1.100", "status": "bound"},
        {"mac-address": "AA:BB:CC:DD:EE:FF", "address": "192.168.1.101", "status": "waiting"},
    ]

    update_resource = MagicMock()
    update_resource.get.return_value = [{
        "installed-version": "7.10",
        "latest-version": "7.11",
        "channel": "stable",
    }]
    update_resource.call = MagicMock()

    system_control = MagicMock()
    system_control.call = MagicMock()

    def get_resource(path: str) -> MagicMock:
        resources = {
            "/system/identity": identity_resource,
            "/system/resource": system_resource,
            "/interface": interface_resource,
            "/log": log_resource,
            "/ip/dhcp-server/lease": dhcp_resource,
            "/system/package/update": update_resource,
            "/system": system_control,
        }
        return resources.get(path, MagicMock())

    api.get_resource = get_resource
    return api


@pytest.fixture
def mock_mikrotik_connection(mock_mikrotik_api: MagicMock) -> MagicMock:
    """Create a mock MikroTik connection pool."""
    connection = MagicMock()
    connection.get_api.return_value = mock_mikrotik_api
    connection.disconnect = MagicMock()
    return connection
