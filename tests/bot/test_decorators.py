"""Tests for app.bot.decorators module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.decorators import restricted, restricted_callback, authorized, authorized_callback


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


class TestAuthorizedDecorator:
    """Tests for @authorized decorator (allows admin and regular users)."""

    @pytest.fixture
    def mock_config_with_users(self, sample_config):
        """Patch get_config to return config with regular users."""
        # Create a config with both admin and regular users
        config = MagicMock()
        config.admin_ids = frozenset([123456789])
        config.user_ids = frozenset([111111111])
        config.is_authorized = lambda uid: uid in config.admin_ids or uid in config.user_ids
        config.is_admin = lambda uid: uid in config.admin_ids
        
        with patch("app.bot.decorators.get_config", return_value=config):
            yield config

    async def test_allows_admin_user(self, mock_config_with_users, mock_update, mock_context):
        """Admin user should be allowed to execute the handler."""
        handler_called = False

        @authorized
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update, mock_context)

        assert handler_called
        assert result == "success"

    async def test_allows_regular_user(self, mock_config_with_users, mock_context):
        """Regular user should be allowed to execute the handler."""
        # Create update for regular user
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 111111111  # Regular user ID
        mock_update.message = AsyncMock()
        
        handler_called = False

        @authorized
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update, mock_context)

        assert handler_called
        assert result == "success"

    async def test_blocks_unauthorized_user(self, mock_config_with_users, mock_context):
        """Unauthorized user (not admin or regular user) should be blocked."""
        # Create update for unauthorized user
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 999999999  # Unauthorized user ID
        mock_update.message = AsyncMock()
        
        handler_called = False

        @authorized
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update, mock_context)

        assert not handler_called
        assert result is None

    async def test_blocks_no_user(self, mock_config_with_users, mock_update_no_user, mock_context):
        """Update with no user should be blocked."""
        handler_called = False

        @authorized
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_no_user, mock_context)

        assert not handler_called
        assert result is None


class TestAuthorizedCallbackDecorator:
    """Tests for @authorized_callback decorator."""

    @pytest.fixture
    def mock_config_with_users(self, sample_config):
        """Patch get_config to return config with regular users."""
        config = MagicMock()
        config.admin_ids = frozenset([123456789])
        config.user_ids = frozenset([111111111])
        config.is_authorized = lambda uid: uid in config.admin_ids or uid in config.user_ids
        config.is_admin = lambda uid: uid in config.admin_ids
        
        with patch("app.bot.decorators.get_config", return_value=config):
            yield config

    async def test_allows_admin_user(self, mock_config_with_users, mock_update_callback, mock_context):
        """Admin user should be allowed to execute the callback handler."""
        handler_called = False

        @authorized_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update_callback, mock_context)

        assert handler_called
        assert result == "success"

    async def test_allows_regular_user(self, mock_config_with_users, mock_context):
        """Regular user should be allowed to execute the callback handler."""
        # Create callback update for regular user
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 111111111  # Regular user ID
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.answer = AsyncMock()
        
        handler_called = False

        @authorized_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update, mock_context)

        assert handler_called
        assert result == "success"

    async def test_blocks_unauthorized_user(self, mock_config_with_users, mock_context):
        """Unauthorized user should be blocked."""
        # Create callback update for unauthorized user
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 999999999
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.answer = AsyncMock()
        
        handler_called = False

        @authorized_callback
        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True
            return "success"

        result = await test_handler(mock_update, mock_context)

        assert not handler_called
        assert result is None
        mock_update.callback_query.answer.assert_called_once()
