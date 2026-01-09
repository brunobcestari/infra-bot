"""Middleware functions for MikroTik handlers."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Try to import MFA system
try:
    from ...mfa import decorators as mfa_decorators
    MFA_AVAILABLE = True
except ImportError:
    mfa_decorators = None
    MFA_AVAILABLE = False


# Set of actions that require MFA verification
# Note: This is AUTO-POPULATED by command_registry.register_all_commands()
# Do not manually add items here - add SensitiveCommand to command_registry.py instead!
#
# Flow:
# 1. Command has @requires_mfa (fail-early check for UX)
# 2. This set is used for execution-time recheck (in case session expired)
SENSITIVE_ACTIONS: set[str] = set()  # Auto-populated at startup


async def check_mfa_for_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str
) -> bool:
    """Check MFA for callback queries.

    Args:
        update: Telegram update object
        context: Callback context
        action: The action being performed

    Returns:
        True if MFA check passes (or not required), False otherwise
    """
    # If action is not sensitive, allow it
    if action not in SENSITIVE_ACTIONS:
        return True

    # If MFA is not available, deny sensitive actions
    if not MFA_AVAILABLE or mfa_decorators is None:
        logger.error("MFA system not available")
        return False

    query = update.callback_query
    user = update.effective_user

    if user is None or query is None:
        return False

    # Access MFA system components
    if mfa_decorators._session_manager is None or mfa_decorators._mfa_db is None:
        logger.error("MFA system not initialized")
        await query.answer("MFA system error")
        return False

    session_manager = mfa_decorators._session_manager
    mfa_db = mfa_decorators._mfa_db

    # Check if user is enrolled
    if not mfa_db.is_user_enrolled(user.id):
        await query.answer("MFA required - not enrolled")
        await query.edit_message_text(
            "⚠️ *MFA Required*\n\n"
            "This action requires Multi-Factor Authentication.\n\n"
            "Please ask your infrastructure administrator to enroll you using:\n"
            f"`python scripts/manage_mfa.py enroll {user.id}`",
            parse_mode='Markdown'
        )
        return False

    # Check if user has valid session
    if session_manager.has_valid_session(user.id):
        logger.info(f"User {user.id} executing callback with valid MFA session")
        return True

    # No valid session - request MFA
    await query.answer("MFA verification required")
    context.user_data['mfa_pending_callback'] = query.data
    context.user_data['mfa_callback_message_id'] = query.message.message_id
    await query.edit_message_text(
        "🔐 *MFA Verification Required*\n\n"
        "Please enter your 6-digit authentication code in the chat:",
        parse_mode='Markdown'
    )
    return False
