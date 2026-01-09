"""Tests for app.mikrotik.keyboards module."""

from unittest.mock import patch

import pytest

from app.mikrotik.keyboards import (
    device_selection_keyboard,
    confirmation_keyboard,
    upgrade_available_keyboard,
    parse_callback_data,
)


class TestDeviceSelectionKeyboard:
    """Tests for device_selection_keyboard function."""

    def test_creates_keyboard_with_devices(self, sample_config):
        """Should create keyboard with device buttons."""
        with patch("app.mikrotik.keyboards.get_config", return_value=sample_config):
            keyboard = device_selection_keyboard("status")

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
        button = keyboard.inline_keyboard[0][0]
        assert button.text == "Test Router"
        assert button.callback_data == "mt:status:test_router"


class TestConfirmationKeyboard:
    """Tests for confirmation_keyboard function."""

    def test_creates_confirmation_keyboard(self):
        """Should create Yes/No confirmation keyboard."""
        keyboard = confirmation_keyboard("reboot", "test_router")

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2
        yes_button, no_button = keyboard.inline_keyboard[0]

        assert "Yes" in yes_button.text
        assert yes_button.callback_data == "mt:reboot_yes:test_router"
        assert "Cancel" in no_button.text
        assert no_button.callback_data == "mt:reboot_no:test_router"


class TestUpgradeAvailableKeyboard:
    """Tests for upgrade_available_keyboard function."""

    def test_creates_upgrade_keyboard(self):
        """Should create Install/Cancel keyboard."""
        keyboard = upgrade_available_keyboard("test_router")

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2
        install_button, cancel_button = keyboard.inline_keyboard[0]

        assert "Install" in install_button.text
        assert install_button.callback_data == "mt:upgrade_yes:test_router"


class TestParseCallbackData:
    """Tests for parse_callback_data function."""

    def test_valid_callback_data(self):
        """Should parse valid callback data."""
        result = parse_callback_data("mt:status:main_router")
        assert result == ("status", "main_router")

    def test_invalid_prefix(self):
        """Should return None for invalid prefix."""
        result = parse_callback_data("xx:status:main_router")
        assert result is None

    def test_invalid_format(self):
        """Should return None for invalid format."""
        result = parse_callback_data("mt:status")
        assert result is None

    def test_empty_string(self):
        """Should return None for empty string."""
        result = parse_callback_data("")
        assert result is None
