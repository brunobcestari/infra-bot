"""Handler registration for MikroTik bot."""

from telegram.ext import Application, CommandHandler

from ..command_registry import register_all_commands
from . import commands


def register_handlers(app: Application) -> None:
    """Register all MikroTik handlers with the bot.

    Args:
        app: Telegram application instance
    """
    # Register convention-based commands (auto-generates everything!)
    register_all_commands(app)

    # Register /start and /help (they show dynamically generated help text)
    app.add_handler(CommandHandler("start", commands.cmd_start))
    app.add_handler(CommandHandler("help", commands.cmd_start))
