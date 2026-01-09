"""Tests for app.mikrotik.client module."""

from unittest.mock import MagicMock, patch
import ssl

import pytest

from app.mikrotik.client import MikroTikClient, get_client, get_all_clients


@pytest.fixture
def mock_ssl_context():
    """Mock SSL context creation."""
    with patch.object(ssl, "create_default_context") as mock_ctx:
        mock_ctx.return_value = MagicMock()
        yield mock_ctx


class TestMikroTikClient:
    """Tests for MikroTikClient class."""

    def test_init(self, sample_mikrotik_device, mock_ssl_context):
        """Client should initialize with device config."""
        client = MikroTikClient(sample_mikrotik_device)
        assert client.device == sample_mikrotik_device

    def test_connect_context_manager(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Connect should work as context manager and cleanup."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            with client.connect() as api:
                assert api is not None

            mock_mikrotik_connection.disconnect.assert_called_once()

    def test_connect_cleanup_on_exception(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Connect should cleanup even when exception occurs."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            with pytest.raises(ValueError):
                with client.connect():
                    raise ValueError("Test error")

            mock_mikrotik_connection.disconnect.assert_called_once()

    def test_get_identity(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return router identity."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            identity = client.get_identity()

        assert identity == "TestRouter"

    def test_get_identity_unknown(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return 'Unknown' when identity not found."""
        client = MikroTikClient(sample_mikrotik_device)
        mock_mikrotik_connection.get_api().get_resource("/system/identity").get.return_value = []

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            identity = client.get_identity()

        assert identity == "Unknown"

    def test_get_system_resource(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return system resource dict."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            resource = client.get_system_resource()

        assert resource["cpu-load"] == "5"
        assert resource["version"] == "7.10"

    def test_get_system_resource_empty(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return empty dict when no resource found."""
        client = MikroTikClient(sample_mikrotik_device)
        mock_mikrotik_connection.get_api().get_resource("/system/resource").get.return_value = []

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            resource = client.get_system_resource()

        assert resource == {}

    def test_get_interfaces(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return list of interfaces."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            interfaces = client.get_interfaces()

        assert len(interfaces) == 2
        assert interfaces[0]["name"] == "ether1"

    def test_get_logs(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return list of log entries."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            logs = client.get_logs(limit=5)

        assert len(logs) == 2
        assert logs[0]["message"] == "Test log 1"

    def test_get_logs_empty(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return empty list when no logs."""
        client = MikroTikClient(sample_mikrotik_device)
        mock_mikrotik_connection.get_api().get_resource("/log").get.return_value = []

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            logs = client.get_logs()

        assert logs == []

    def test_get_dhcp_leases(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return list of DHCP leases."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            leases = client.get_dhcp_leases()

        assert len(leases) == 2
        assert leases[0]["host-name"] == "device1"

    def test_get_services_enabled(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return list of enabled services."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            services = client.get_services_enabled()

        assert len(services) == 2
        assert services[0]["name"] == "ssh"

    def test_check_for_updates(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should check for updates and return result."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            updates = client.check_for_updates()

        assert updates["installed-version"] == "7.10"
        assert updates["latest-version"] == "7.11"
        # Should call check-for-updates
        mock_mikrotik_connection.get_api().get_resource("/system/package/update").call.assert_called_with("check-for-updates")

    def test_install_updates(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should call install on package update."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            client.install_updates()

        mock_mikrotik_connection.get_api().get_resource("/system/package/update").call.assert_called_with("install")

    def test_reboot(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should call reboot on system."""
        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            client.reboot()

        mock_mikrotik_connection.get_api().get_resource("/system").call.assert_called_with("reboot")


class TestGetClient:
    """Tests for get_client function."""

    def test_get_client_found(self, sample_config, mock_ssl_context):
        """Should return client for existing device."""
        with patch("app.mikrotik.client.get_config", return_value=sample_config):
            client = get_client("test_router")

        assert client is not None
        assert client.device.slug == "test_router"

    def test_get_client_not_found(self, sample_config):
        """Should return None for non-existent device."""
        with patch("app.mikrotik.client.get_config", return_value=sample_config):
            client = get_client("nonexistent")

        assert client is None


class TestGetAllClients:
    """Tests for get_all_clients function."""

    def test_get_all_clients(self, sample_config, mock_ssl_context):
        """Should return clients for all devices."""
        with patch("app.mikrotik.client.get_config", return_value=sample_config):
            clients = get_all_clients()

        assert len(clients) == 1
        assert clients[0].device.slug == "test_router"
