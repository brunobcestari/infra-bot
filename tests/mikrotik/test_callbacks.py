"""Tests for app.mikrotik.callbacks module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mikrotik.command_base import SimpleCommand, SensitiveCommand


class TestSimpleCommand:
    """Tests for SimpleCommand class."""

    def test_creates_command(self):
        """Should create a simple command."""
        cmd = SimpleCommand(
            name="test",
            description="Test command",
            client_method="get_something",
            formatter="format_something"
        )

        assert cmd.name == "test"
        assert cmd.description == "Test command"
        assert cmd.client_method == "get_something"
        assert cmd.formatter == "format_something"

    def test_generates_help_text(self):
        """Should generate help text."""
        cmd = SimpleCommand(
            name="test",
            description="Test command",
            client_method="get_something",
            formatter="format_something"
        )

        help_text = cmd.get_help_text()
        assert "/test" in help_text
        assert "Test command" in help_text


class TestSensitiveCommand:
    """Tests for SensitiveCommand class."""

    def test_creates_sensitive_command(self):
        """Should create a sensitive command with MFA."""
        cmd = SensitiveCommand(
            name="dangerous",
            description="Dangerous operation",
            client_method="do_something",
            confirmation_formatter="format_confirmation",
            success_message="Done!"
        )

        assert cmd.name == "dangerous"
        assert cmd.description == "Dangerous operation"
        assert cmd.help_emoji == "🔐"

    def test_generates_help_text_with_emoji(self):
        """Should generate help text with lock emoji."""
        cmd = SensitiveCommand(
            name="dangerous",
            description="Dangerous operation",
            client_method="do_something",
            confirmation_formatter="format_confirmation",
            success_message="Done!"
        )

        help_text = cmd.get_help_text()
        assert "/dangerous" in help_text
        assert "Dangerous operation" in help_text
        assert "🔐" in help_text
