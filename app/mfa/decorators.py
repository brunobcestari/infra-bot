"""MFA decorators for protecting commands and callbacks."""

import logging
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from .session import SessionManager
from .database import MFADatabase

logger = logging.getLogger(__name__)

# Module-level instances (initialized by init_mfa_decorators)
_session_manager: SessionManager | None = None
_mfa_db: MFADatabase | None = None


def init_mfa_decorators(session_manager: SessionManager, mfa_db: MFADatabase) -> None:
    """Initialize MFA decorator system.

    Must be called before using decorators.

    Args:
        session_manager: SessionManager instance
        mfa_db: MFADatabase instance
    """
    global _session_manager, _mfa_db
    _session_manager = session_manager
    _mfa_db = mfa_db
    logger.info("MFA decorators initialized")


def requires_mfa(func):
    """Decorator to require MFA verification for sensitive commands.

    Should be applied AFTER @restricted decorator:
        @restricted
        @requires_mfa
        async def cmd_upgrade(...):
            ...

    If user is not enrolled, prompts to enroll via CLI script.
    If user has no valid session, prompts for TOTP code.
    If user has valid session, allows command to proceed.

    Args:
        func: Async command handler function

    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if _session_manager is None or _mfa_db is None:
            logger.error("MFA system not initialized")
            await update.message.reply_text(
                "MFA system error. Please contact administrator."
            )
            return None

        user = update.effective_user
        if user is None:
            return None

        # Check if user is enrolled in MFA
        if not _mfa_db.is_user_enrolled(user.id):
            await update.message.reply_text(
                "⚠️ *MFA Required*\n\n"
                "This command requires Multi-Factor Authentication.\n\n"
                "Please ask your infrastructure administrator to enroll you using:\n"
                f"`python scripts/manage_mfa.py enroll {user.id}`",
                parse_mode='Markdown'
            )
            return None

        # Check if user has valid session
        if _session_manager.has_valid_session(user.id):
            # Session valid, proceed with command
            logger.info(f"User {user.id} executing {func.__name__} with valid MFA session")
            return await func(update, context, *args, **kwargs)

        # No valid session, initiate MFA challenge
        await _initiate_mfa_challenge(update, context, func.__name__)
        return None

    return wrapped


def requires_mfa_callback(func):
    """Decorator for callback queries that require MFA.

    Should be applied AFTER @restricted_callback:
        @restricted_callback
        @requires_mfa_callback
        async def handle_callback(...):
            ...

    Args:
        func: Async callback handler function

    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if _session_manager is None or _mfa_db is None:
            logger.error("MFA system not initialized")
            return None

        user = update.effective_user
        query = update.callback_query

        if user is None or query is None:
            return None

        # Check enrollment
        if not _mfa_db.is_user_enrolled(user.id):
            await query.answer("MFA required - not enrolled")
            await query.edit_message_text(
                "⚠️ *MFA Required*\n\n"
                "This action requires Multi-Factor Authentication.\n\n"
                "Please ask your infrastructure administrator to enroll you using:\n"
                f"`python scripts/manage_mfa.py enroll {user.id}`",
                parse_mode='Markdown'
            )
            return None

        # Check session
        if _session_manager.has_valid_session(user.id):
            logger.info(f"User {user.id} executing callback {func.__name__} with valid MFA session")
            return await func(update, context, *args, **kwargs)

        # No valid session
        await query.answer("MFA verification required")

        # Store callback data for later retry
        context.user_data['mfa_pending_callback'] = query.data
        context.user_data['mfa_callback_message_id'] = query.message.message_id

        await query.edit_message_text(
            "🔐 *MFA Verification Required*\n\n"
            "Please enter your 6-digit authentication code in the chat:",
            parse_mode='Markdown'
        )
        return None

    return wrapped


async def _initiate_mfa_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str) -> None:
    """Prompt user for TOTP code.

    Args:
        update: Telegram update
        context: Bot context
        command_name: Name of the command being protected
    """
    # Store the original command in user_data for retry instruction
    context.user_data['mfa_pending_command'] = command_name

    await update.message.reply_text(
        "🔐 *MFA Verification Required*\n\n"
        "Please enter your 6-digit authentication code:",
        parse_mode='Markdown'
    )
