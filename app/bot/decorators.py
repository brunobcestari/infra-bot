import logging
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from ..config import get_config

logger = logging.getLogger(__name__)


def restricted(func):
    """Decorator to restrict command access to admin users only.

    Security: Telegram user IDs are authenticated by the Bot API and cannot be spoofed.
    This decorator safely denies access if:
    - No user is associated with the update (channel posts, etc.)
    - User ID is not in the admin list
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            logger.warning("Rejected update with no effective_user")
            return None

        config = get_config()
        if user.id not in config.admin_ids:
            logger.warning(f"Unauthorized access denied for user {user.id}")
            return None

        return await func(update, context, *args, **kwargs)
    return wrapped


def restricted_callback(func):
    """Decorator to restrict callback queries to admin users only."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        query = update.callback_query

        if user is None or query is None:
            logger.warning("Rejected callback with no user or query")
            return None

        config = get_config()
        if user.id not in config.admin_ids:
            logger.warning(f"Unauthorized callback denied for user {user.id}")
            await query.answer()
            return None

        return await func(update, context, *args, **kwargs)
    return wrapped


def authorized(func):
    """Decorator to restrict command access to authorized users (admin or regular users).

    Security: Telegram user IDs are authenticated by the Bot API and cannot be spoofed.
    This decorator safely denies access if:
    - No user is associated with the update (channel posts, etc.)
    - User ID is not in the admin or user list
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            logger.warning("Rejected update with no effective_user")
            return None

        config = get_config()
        if not config.is_authorized(user.id):
            logger.warning(f"Unauthorized access denied for user {user.id}")
            return None

        return await func(update, context, *args, **kwargs)
    return wrapped


def authorized_callback(func):
    """Decorator to restrict callback queries to authorized users (admin or regular users)."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        query = update.callback_query

        if user is None or query is None:
            logger.warning("Rejected callback with no user or query")
            return None

        config = get_config()
        if not config.is_authorized(user.id):
            logger.warning(f"Unauthorized callback denied for user {user.id}")
            await query.answer()
            return None

        return await func(update, context, *args, **kwargs)
    return wrapped
