"""MFA command handlers for Telegram bot."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ..bot.decorators import restricted
from ..config import get_config
from .totp import verify_totp_code
from .database import MFADatabase
from .session import SessionManager

logger = logging.getLogger(__name__)

# Module-level instances (set by register_mfa_handlers)
_mfa_db: MFADatabase | None = None
_session_manager: SessionManager | None = None


# --- Status Command ---

@restricted
async def cmd_mfa_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's MFA enrollment and session status."""
    user_id = update.effective_user.id

    if not _mfa_db.is_user_enrolled(user_id):
        await update.message.reply_text(
            "❌ *MFA Not Enabled*\n\n"
            "You are not enrolled in Multi-Factor Authentication.\n\n"
            "Ask your infrastructure administrator to enroll you using:\n"
            f"`python scripts/manage_mfa.py enroll {user_id}`",
            parse_mode='Markdown'
        )
        return

    # Get user info
    user_info = _mfa_db.get_user_info(user_id)
    has_session = _session_manager.has_valid_session(user_id)

    # Format timestamps
    created = user_info.get('created_at', 'Unknown')
    last_used = user_info.get('last_used_at') or 'Never'

    status_emoji = "🟢" if has_session else "🔴"
    session_text = f"Active ({_session_manager.default_duration} min)" if has_session else "No active session"

    # Get session details if active
    session_details = ""
    if has_session:
        session_info = _session_manager.get_session_info(user_id)
        if session_info:
            expires_at = session_info.get('expires_at', 'Unknown')
            session_details = f"Expires: {expires_at.split('.')[0]} UTC\n"

    await update.message.reply_text(
        f"✅ *MFA Status*\n\n"
        f"{status_emoji} *Session:* {session_text}\n"
        f"{session_details}"
        f"📅 *Enrolled:* {created.split('.')[0]} UTC\n"
        f"🕐 *Last used:* {last_used.split('.')[0] if last_used != 'Never' else 'Never'} UTC\n\n"
        f"MFA protects critical commands like `/upgrade` and `/reboot`.",
        parse_mode='Markdown'
    )


# --- MFA Verification Handler ---

async def handle_mfa_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle TOTP code verification for command continuation.

    This handler processes 6-digit codes sent by users who are attempting
    to run MFA-protected commands.
    """
    user_id = update.effective_user.id
    message_text = update.message.text.strip()

    # Check if there's a pending command or callback
    pending_command = context.user_data.get('mfa_pending_command')
    pending_callback = context.user_data.get('mfa_pending_callback')

    if not pending_command and not pending_callback:
        # Not in MFA verification flow, ignore
        return

    # Validate code format
    if not message_text.isdigit() or len(message_text) != 6:
        await update.message.reply_text(
            "❌ Invalid code format.\n\n"
            "Please send a 6-digit number from your authenticator app."
        )
        return

    # Get user's secret
    secret = _mfa_db.get_user_secret(user_id)
    if not secret:
        await update.message.reply_text(
            "❌ MFA not set up. Please contact your administrator."
        )
        # Clear pending data
        context.user_data.pop('mfa_pending_command', None)
        context.user_data.pop('mfa_pending_callback', None)
        return

    # Check rate limiting
    if _mfa_db.is_rate_limited(user_id):
        await update.message.reply_text(
            "⏸️ *Too Many Failed Attempts*\n\n"
            "Please wait 15 minutes before trying again.\n\n"
            "If you've lost access to your authenticator, contact your administrator.",
            parse_mode='Markdown'
        )
        return

    # Verify TOTP code
    if not verify_totp_code(secret, message_text):
        _mfa_db.increment_failed_attempts(user_id)
        _mfa_db.log_event(user_id, 'verification_failed', {})

        attempts_left = 5 - _mfa_db.get_user_info(user_id).get('failed_attempts', 0)
        attempts_text = f"\n\n⚠️ {attempts_left} attempts remaining." if attempts_left > 0 else ""

        await update.message.reply_text(
            f"❌ *Invalid Authentication Code*\n\n"
            f"The code you entered is incorrect. Please try again.{attempts_text}\n\n"
            f"Make sure your device time is synchronized.",
            parse_mode='Markdown'
        )
        return

    # Success! Reset failed attempts and create session
    _mfa_db.reset_failed_attempts(user_id)
    _mfa_db.update_last_used(user_id)
    session_id = _session_manager.create_session(user_id)
    _mfa_db.log_event(user_id, 'verification_success', {'session_id': session_id})

    logger.info(f"User {user_id} successfully verified MFA")

    await update.message.reply_text(
        f"✅ *Verification Successful!*\n\n"
        f"Your MFA session is active for {_session_manager.default_duration} minutes.\n\n"
        f"You can now run your command again.",
        parse_mode='Markdown'
    )

    # Clear pending data
    if pending_command:
        command_display = pending_command.replace('cmd_', '/')
        await update.message.reply_text(
            f"Please run your command again: `{command_display}`",
            parse_mode='Markdown'
        )
        context.user_data.pop('mfa_pending_command', None)

    if pending_callback:
        await update.message.reply_text(
            "Please click the button again to continue."
        )
        context.user_data.pop('mfa_pending_callback', None)
        context.user_data.pop('mfa_callback_message_id', None)


# --- Registration ---

def register_mfa_handlers(app: Application, mfa_db: MFADatabase, session_manager: SessionManager) -> None:
    """Register all MFA handlers with the bot application.

    Args:
        app: Telegram bot application
        mfa_db: MFA database instance
        session_manager: Session manager instance
    """
    global _mfa_db, _session_manager
    _mfa_db = mfa_db
    _session_manager = session_manager

    # Commands
    app.add_handler(CommandHandler("mfa_status", cmd_mfa_status))

    # Message handler for TOTP codes (low priority, must be after command handlers)
    # Only process messages from admin users (security)
    config = get_config()
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=list(config.admin_ids)),
        handle_mfa_verification
    ))

    logger.info("MFA handlers registered")
