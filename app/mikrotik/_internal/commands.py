"""Custom command handlers for MikroTik bot.

Most commands are now auto-generated via command_registry.py!
This file only contains the /start and /help commands.
"""

from telegram import Update
from telegram.ext import ContextTypes

from ...bot.decorators import authorized
from ...config import get_config
from ..command_registry import get_help_text


@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message with available commands.

    Help text is automatically generated from command_registry.py.
    """
    user = update.effective_user
    config = get_config()
    show_admin_commands = config.is_admin(user.id) if user else False
    
    help_text = get_help_text(show_admin_commands=show_admin_commands)
    await update.message.reply_text(help_text, parse_mode='Markdown')
