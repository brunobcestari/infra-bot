"""Tests for app.bot.decorators module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.decorators import restricted, restricted_callback


class TestRestrictedDecorator:
    """Tests for @restricted decorator."""

    @pytest.fixture
    def mock_config(self, sample_config):
        """Patch get_config to return sample config."""
        with patch("app.bot.decorators.get_config", return_value=sample_config):
            yield sample_config

    async def test_allows_authorized_user(self, mock_config, mock_update, mock_context):
        """Authorized user should be allowed to execute the handler."""
        handler_called = False

        @restricted
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update, mock_context)

        assert handler_called
        assert result == "success"

    async def test_blocks_unauthorized_user(self, mock_config, mock_update_unauthorized, mock_context):
        """Unauthorized user should be blocked."""
        handler_called = False

        @restricted
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_unauthorized, mock_context)

        assert not handler_called
        assert result is None

    async def test_blocks_no_user(self, mock_config, mock_update_no_user, mock_context):
        """Update with no user should be blocked."""
        handler_called = False

        @restricted
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_no_user, mock_context)

        assert not handler_called
        assert result is None

    async def test_preserves_function_name(self, mock_config):
        """Decorator should preserve the original function name."""

        @restricted
        async def my_handler(update, context):
            pass

        assert my_handler.__name__ == "my_handler"

    async def test_logs_unauthorized_access(self, mock_config, mock_update_unauthorized, mock_context):
        """Should log unauthorized access attempts."""

        @restricted
        async def test_handler(update, context):
            pass

        with patch("app.bot.decorators.logger") as mock_logger:
            await test_handler(mock_update_unauthorized, mock_context)
            mock_logger.warning.assert_called_once()
            assert "999999999" in str(mock_logger.warning.call_args)


class TestRestrictedCallbackDecorator:
    """Tests for @restricted_callback decorator."""

    @pytest.fixture
    def mock_config(self, sample_config):
        """Patch get_config to return sample config."""
        with patch("app.bot.decorators.get_config", return_value=sample_config):
            yield sample_config

    async def test_allows_authorized_user(self, mock_config, mock_update_callback, mock_context):
        """Authorized user should be allowed to execute the callback handler."""
        handler_called = False

        @restricted_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_callback, mock_context)

        assert handler_called
        assert result == "success"

    async def test_blocks_unauthorized_user(self, mock_config, mock_update_callback, mock_context):
        """Unauthorized user should be blocked."""
        # Change user to unauthorized
        mock_update_callback.effective_user.id = 999999999
        handler_called = False

        @restricted_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_callback, mock_context)

        assert not handler_called
        assert result is None
        # Should answer the callback query (to dismiss loading)
        mock_update_callback.callback_query.answer.assert_called_once()

    async def test_blocks_no_user(self, mock_config, mock_update_callback, mock_context):
        """Update with no user should be blocked."""
        mock_update_callback.effective_user = None
        handler_called = False

        @restricted_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_callback, mock_context)

        assert not handler_called
        assert result is None

    async def test_blocks_no_query(self, mock_config, mock_update_callback, mock_context):
        """Update with no callback query should be blocked."""
        mock_update_callback.callback_query = None
        handler_called = False

        @restricted_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_callback, mock_context)

        assert not handler_called
        assert result is None

    async def test_preserves_function_name(self, mock_config):
        """Decorator should preserve the original function name."""

        @restricted_callback
        async def my_callback_handler(update, context):
            pass

        assert my_callback_handler.__name__ == "my_callback_handler"
