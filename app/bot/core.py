"""Bot core setup and initialization."""

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes

from ..config import get_config

logger = logging.getLogger(__name__)


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors without exposing details to users."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "An error occurred. Please try again later."
            )
        except Exception:
            pass  # Best effort to notify user


def create_bot() -> Application:
    """Create and configure the Telegram bot application."""
    config = get_config()

    app = ApplicationBuilder().token(config.telegram_token).build()
    app.add_error_handler(error_handler)

    return app
