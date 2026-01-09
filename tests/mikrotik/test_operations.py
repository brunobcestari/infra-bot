"""Tests for app.mikrotik.operations module."""

from unittest.mock import MagicMock, patch
import ssl

import pytest

from app.mikrotik.operations import (
    execute_operation,
    get_status,
    get_interfaces,
    get_leases,
    check_updates,
)


class TestExecuteOperation:
    """Tests for execute_operation helper."""

    @pytest.mark.asyncio
    async def test_executes_successful_operation(self, sample_config, mock_ssl_context):
        """Should execute operation and return result."""
        def dummy_operation(client):
            from app.mikrotik.operations import OperationResult
            return OperationResult(success=True, message="Success")

        with patch("app.mikrotik.operations.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = await execute_operation("test_router", dummy_operation)

        assert result.success is True
        assert result.message == "Success"

    @pytest.mark.asyncio
    async def test_handles_device_not_found(self):
        """Should return error when device not found."""
        def dummy_operation(client):
            pass

        with patch("app.mikrotik.operations.get_client", return_value=None):
            result = await execute_operation("nonexistent", dummy_operation)

        assert result.success is False
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_handles_operation_exception(self, sample_config, mock_ssl_context):
        """Should handle exceptions during operation."""
        def failing_operation(client):
            raise ValueError("Test error")

        with patch("app.mikrotik.operations.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.device.name = "Test Router"
            mock_get_client.return_value = mock_client

            result = await execute_operation("test_router", failing_operation, "Failed")

        assert result.success is False
        assert "Failed" in result.message


class TestGetStatus:
    """Tests for get_status operation."""

    def test_returns_formatted_status(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return formatted status message."""
        from app.mikrotik.client import MikroTikClient

        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            result = get_status(client)

        assert result.success is True
        assert "TestRouter" in result.message
        assert "CPU" in result.message


class TestGetInterfaces:
    """Tests for get_interfaces operation."""

    def test_returns_formatted_interfaces(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return formatted interfaces message."""
        from app.mikrotik.client import MikroTikClient

        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            result = get_interfaces(client)

        assert result.success is True
        assert "ether1" in result.message


class TestGetLeases:
    """Tests for get_leases operation."""

    def test_returns_formatted_leases(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return formatted leases message."""
        from app.mikrotik.client import MikroTikClient

        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            result = get_leases(client)

        assert result.success is True
        assert "device1" in result.message


class TestCheckUpdates:
    """Tests for check_updates operation."""

    def test_returns_up_to_date_message(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return up-to-date message when no updates."""
        from app.mikrotik.client import MikroTikClient

        client = MikroTikClient(sample_mikrotik_device)

        # Mock update resource to show same version
        mock_mikrotik_connection.get_api().get_resource("/system/package/update").get.return_value = [{
            "installed-version": "7.10",
            "latest-version": "7.10",
            "channel": "stable",
        }]

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            result = check_updates(client)

        assert result.success is True
        assert "latest version" in result.message
        assert result.keyboard is None

    def test_returns_update_available_with_keyboard(self, sample_mikrotik_device, mock_mikrotik_connection, mock_ssl_context):
        """Should return update message when update available."""
        from app.mikrotik.client import MikroTikClient

        client = MikroTikClient(sample_mikrotik_device)

        with patch.object(client, "_create_connection", return_value=mock_mikrotik_connection):
            result = check_updates(client)

        assert result.success is True
        # Message says "Update Available!"
        assert "Available" in result.message or "available" in result.message.lower()
        # Note: keyboard removed - now suggests /upgrade command instead
        assert result.keyboard is not None  # Still has keyboard for backward compat
