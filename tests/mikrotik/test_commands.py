"""Tests for app.mikrotik.commands module."""

from unittest.mock import patch

import pytest

from app.mikrotik.commands import cmd_start
from app.mikrotik.command_registry import SIMPLE_COMMANDS, SENSITIVE_COMMANDS


class TestCmdStart:
    """Tests for cmd_start handler."""

    @pytest.fixture
    def mock_decorators(self, sample_config):
        """Patch decorators and config."""
        with patch("app.bot.decorators.get_config", return_value=sample_config):
            yield

    async def test_sends_help_message(self, mock_decorators, mock_update, mock_context):
        """Should send help message with available commands."""
        await cmd_start.__wrapped__(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        help_text = call_args[0][0]

        # Check that help includes registered commands
        assert "Management Bot" in help_text
        assert "/status" in help_text or "status" in help_text.lower()


class TestCommandRegistry:
    """Tests for command registry."""

    def test_has_simple_commands(self):
        """Should have simple commands registered."""
        assert len(SIMPLE_COMMANDS) > 0

        # Check we have expected commands
        command_names = {cmd.name for cmd in SIMPLE_COMMANDS}
        assert "status" in command_names
        assert "interfaces" in command_names
        assert "updates" in command_names

    def test_has_sensitive_commands(self):
        """Should have sensitive commands registered."""
        assert len(SENSITIVE_COMMANDS) > 0

        # Check we have expected commands
        command_names = {cmd.name for cmd in SENSITIVE_COMMANDS}
        assert "reboot" in command_names
        assert "upgrade" in command_names

    def test_command_properties(self):
        """Should have proper command properties."""
        cmd = SIMPLE_COMMANDS[0]

        assert hasattr(cmd, 'name')
        assert hasattr(cmd, 'description')
        assert hasattr(cmd, 'client_method')
        assert hasattr(cmd, 'formatter')
        assert hasattr(cmd, 'register')
