"""Tests for app.mikrotik.formatters module."""

import pytest

from app.mikrotik.formatters import (
    format_status_message,
    format_interfaces_message,
    format_leases_message,
    format_services_message,
    format_logs_message,
    format_updates_message,
    format_update_current_message,
    format_update_available_message,
)


class TestFormatStatusMessage:
    """Tests for format_status_message."""

    def test_formats_status_correctly(self):
        """Should format system status with all fields."""
        resource = {
            "cpu-load": "5",
            "free-memory": "500000000",
            "total-memory": "1000000000",
            "free-hdd-space": "100000000",
            "total-hdd-space": "500000000",
            "uptime": "1d2h3m4s",
            "board-name": "RB4011",
            "version": "7.10",
            "architecture-name": "arm64",
        }

        message = format_status_message("TestRouter", resource)

        assert "TestRouter" in message
        assert "5%" in message
        assert "CPU" in message
        assert "Memory" in message
        assert "Disk" in message


class TestFormatInterfacesMessage:
    """Tests for format_interfaces_message."""

    def test_formats_interfaces_list(self):
        """Should format interface list correctly."""
        interfaces = [
            {
                "name": "ether1",
                "type": "ether",
                "running": "true",
                "disabled": "false",
                "tx-byte": "1000000",
                "rx-byte": "2000000",
            }
        ]

        message = format_interfaces_message("TestRouter", interfaces)

        assert "TestRouter" in message
        assert "ether1" in message
        assert "✅" in message


class TestFormatLeasesMessage:
    """Tests for format_leases_message."""

    def test_formats_leases_list(self):
        """Should format DHCP leases correctly."""
        leases = [
            {"host-name": "device1", "address": "192.168.1.100", "status": "bound"}
        ]

        message = format_leases_message("TestRouter", leases)

        assert "TestRouter" in message
        assert "device1" in message
        assert "192.168.1.100" in message

    def test_handles_empty_leases(self):
        """Should handle empty leases list."""
        message = format_leases_message("TestRouter", [])

        assert "No DHCP leases found" in message


class TestFormatServicesMessage:
    """Tests for format_services_message."""

    def test_formats_services_list(self):
        """Should format enabled services correctly."""
        services = [
            {
                "name": "ssh",
                "port": "22",
                "proto": "tcp",
                "address": "0.0.0.0",
                "certificate": "none",
            }
        ]

        message = format_services_message("TestRouter", services)

        assert "TestRouter" in message
        assert "ssh" in message
        assert "22" in message

    def test_handles_empty_services(self):
        """Should handle empty services list."""
        message = format_services_message("TestRouter", [])

        assert "No enabled IP services found" in message


class TestFormatLogsMessage:
    """Tests for format_logs_message."""

    def test_formats_logs_list(self):
        """Should format log entries correctly."""
        logs = [
            {"time": "12:00:00", "topics": "system", "message": "Test log"}
        ]

        message = format_logs_message("TestRouter", logs)

        assert "TestRouter" in message
        assert "12:00:00" in message
        assert "Test log" in message

    def test_handles_empty_logs(self):
        """Should handle empty logs list."""
        message = format_logs_message("TestRouter", [])

        assert "No log entries found" in message


class TestUpdateMessages:
    """Tests for update-related formatters."""

    def test_format_updates_up_to_date(self):
        """Should format message when system is up to date."""
        update_info = {
            "installed-version": "7.10",
            "latest-version": "7.10",
            "channel": "stable",
        }

        message = format_updates_message("TestRouter", update_info)

        assert "TestRouter" in message
        assert "7.10" in message
        assert "latest version" in message.lower()
        assert "stable" in message

    def test_format_updates_available(self):
        """Should format message when update is available."""
        update_info = {
            "installed-version": "7.10",
            "latest-version": "7.11",
            "channel": "stable",
        }

        message = format_updates_message("TestRouter", update_info)

        assert "TestRouter" in message
        assert "7.10" in message
        assert "7.11" in message
        assert "available" in message.lower()
        assert "/upgrade" in message.lower()

    def test_format_update_current_deprecated(self):
        """Should still work with deprecated function."""
        update_info = {
            "installed-version": "7.10",
            "latest-version": "7.10",
            "channel": "stable",
        }

        message = format_update_current_message("TestRouter", update_info)

        assert "TestRouter" in message
        assert "7.10" in message

    def test_format_update_available_deprecated(self):
        """Should still work with deprecated function."""
        update_info = {
            "installed-version": "7.10",
            "latest-version": "7.11",
            "channel": "stable",
        }

        message = format_update_available_message("TestRouter", update_info)

        assert "TestRouter" in message
        assert "7.10" in message
        assert "7.11" in message
