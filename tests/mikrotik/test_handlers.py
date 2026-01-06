"""Tests for app.mikrotik.handlers module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mikrotik.handlers import (
    _device_keyboard,
    _parse_callback,
    cmd_start,
    cmd_status,
    callback_handler,
    register_handlers,
)


class TestDeviceKeyboard:
    """Tests for _device_keyboard function."""

    def test_creates_keyboard_with_devices(self, sample_config):
        """Should create keyboard with device buttons."""
        with patch("app.mikrotik.handlers.get_config", return_value=sample_config):
            keyboard = _device_keyboard("status")

        assert keyboard is not None
        # Check we have buttons
        assert len(keyboard.inline_keyboard) > 0
        # Check first button
        button = keyboard.inline_keyboard[0][0]
        assert button.text == "Test Router"
        assert button.callback_data == "mt:status:test_router"


class TestParseCallback:
    """Tests for _parse_callback function."""

    def test_valid_callback_data(self):
        """Should parse valid callback data."""
        result = _parse_callback("mt:status:main_router")
        assert result == ("status", "main_router")

    def test_invalid_prefix(self):
        """Should return None for invalid prefix."""
        result = _parse_callback("xx:status:main_router")
        assert result is None

    def test_invalid_format(self):
        """Should return None for invalid format."""
        result = _parse_callback("mt:status")
        assert result is None

    def test_empty_string(self):
        """Should return None for empty string."""
        result = _parse_callback("")
        assert result is None


class TestCmdStart:
    """Tests for cmd_start handler."""

    @pytest.fixture
    def mock_decorators(self, sample_config):
        """Patch decorators and config."""
        with patch("app.mikrotik.handlers.get_config", return_value=sample_config):
            with patch("app.bot.decorators.get_config", return_value=sample_config):
                yield

    async def test_sends_help_message(self, mock_decorators, mock_update, mock_context):
        """Should send help message."""
        # Call the underlying function (bypassing decorator for simplicity)
        await cmd_start.__wrapped__(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Management Bot" in call_args[0][0]


class TestCmdStatus:
    """Tests for cmd_status handler."""

    @pytest.fixture
    def mock_decorators(self, sample_config):
        """Patch decorators and config."""
        with patch("app.mikrotik.handlers.get_config", return_value=sample_config):
            with patch("app.bot.decorators.get_config", return_value=sample_config):
                yield

    async def test_shows_device_selector(self, mock_decorators, mock_update, mock_context):
        """Should show device selection keyboard."""
        await cmd_status.__wrapped__(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Select a device" in call_args[0][0]
        # Check keyboard was passed
        assert call_args[1]["reply_markup"] is not None


class TestCallbackHandler:
    """Tests for callback_handler."""

    @pytest.fixture
    def mock_decorators(self, sample_config):
        """Patch decorators and config."""
        with patch("app.mikrotik.handlers.get_config", return_value=sample_config):
            with patch("app.bot.decorators.get_config", return_value=sample_config):
                yield

    async def test_handles_status_callback(self, mock_decorators, mock_update_callback, mock_context, mock_mikrotik_connection):
        """Should handle status callback."""
        mock_update_callback.callback_query.data = "mt:status:test_router"

        with patch("app.mikrotik.handlers.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.device.name = "Test Router"
            mock_client.get_system_resource.return_value = {
                "cpu-load": "5",
                "free-memory": "500000000",
                "total-memory": "1000000000",
                "free-hdd-space": "100000000",
                "total-hdd-space": "500000000",
                "uptime": "1d2h3m",
                "board-name": "RB4011",
                "version": "7.10",
                "architecture-name": "arm64",
            }
            mock_client.get_identity.return_value = "TestRouter"
            mock_get_client.return_value = mock_client

            await callback_handler.__wrapped__(mock_update_callback, mock_context)

        mock_update_callback.callback_query.answer.assert_called_once()
        mock_update_callback.callback_query.edit_message_text.assert_called_once()

    async def test_handles_invalid_callback(self, mock_decorators, mock_update_callback, mock_context):
        """Should ignore invalid callback data."""
        mock_update_callback.callback_query.data = "invalid:data"

        await callback_handler.__wrapped__(mock_update_callback, mock_context)

        mock_update_callback.callback_query.answer.assert_called_once()
        # edit_message_text should not be called for invalid data
        mock_update_callback.callback_query.edit_message_text.assert_not_called()

    async def test_handles_device_not_found(self, mock_decorators, mock_update_callback, mock_context):
        """Should handle device not found."""
        mock_update_callback.callback_query.data = "mt:status:nonexistent"

        with patch("app.mikrotik.handlers.get_client", return_value=None):
            await callback_handler.__wrapped__(mock_update_callback, mock_context)

        mock_update_callback.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update_callback.callback_query.edit_message_text.call_args
        assert "not found" in call_args[0][0]


class TestRegisterHandlers:
    """Tests for register_handlers function."""

    def test_registers_all_handlers(self):
        """Should register all command and callback handlers."""
        mock_app = MagicMock()

        register_handlers(mock_app)

        # Check command handlers were added
        assert mock_app.add_handler.call_count >= 9  # 9 commands + callbacks

        # Verify some specific handlers were registered
        handler_calls = [str(call) for call in mock_app.add_handler.call_args_list]
        handler_str = str(handler_calls)

        assert "start" in handler_str or "CommandHandler" in handler_str
