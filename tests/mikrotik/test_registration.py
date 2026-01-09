"""Tests for app.mikrotik.registration module."""

from unittest.mock import MagicMock

from app.mikrotik.registration import register_handlers


class TestRegisterHandlers:
    """Tests for register_handlers function."""

    def test_registers_all_command_handlers(self):
        """Should register all command handlers."""
        mock_app = MagicMock()

        register_handlers(mock_app)

        # Should register at least 10 handlers (9 commands + callback handler)
        assert mock_app.add_handler.call_count >= 10

    def test_registers_callback_handler(self):
        """Should register callback handler with pattern."""
        mock_app = MagicMock()

        register_handlers(mock_app)

        # Verify callback handler was registered
        calls = [str(call) for call in mock_app.add_handler.call_args_list]
        handler_str = "".join(calls)

        # Check that CallbackQueryHandler was registered
        assert "CallbackQueryHandler" in handler_str or "callback" in handler_str.lower()
