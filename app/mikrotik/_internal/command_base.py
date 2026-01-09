"""Base classes for convention-based MikroTik commands.

This module provides a clean, declarative way to define bot commands without boilerplate.
Simply instantiate SimpleCommand or SensitiveCommand with the right parameters!
"""

import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from ...bot.decorators import restricted, restricted_callback
from ..client import get_client
from .. import formatters
from .keyboards import device_selection_keyboard, confirmation_keyboard

logger = logging.getLogger(__name__)

# Try to import MFA decorator
try:
    from ...mfa.decorators import requires_mfa
except ImportError:
    def requires_mfa(func):
        return func


class CommandBase(ABC):
    """Base class for all MikroTik commands."""

    def __init__(
        self,
        name: str,
        description: str,
        client_method: str,
        help_emoji: str = ""
    ):
        """Initialize command.

        Args:
            name: Command name (e.g., "status" for /status)
            description: Human-readable description
            client_method: Method name on MikroTikClient to call
            help_emoji: Optional emoji for help text
        """
        self.name = name
        self.description = description
        self.client_method = client_method
        self.help_emoji = help_emoji
        self.callback_prefix = f"mt:{name}"

    @abstractmethod
    def register(self, app: Application) -> None:
        """Register this command's handlers with the bot."""
        pass

    def get_help_text(self) -> str:
        """Get formatted help text for this command."""
        emoji = f" {self.help_emoji}" if self.help_emoji else ""
        return f"/{self.name.replace('_', '\\_')} - {self.description}{emoji}"


class SimpleCommand(CommandBase):
    """A simple read-only command that displays data from a device.

    Perfect for: /status, /interfaces, /logs, /leases, etc.

    Example:
        SimpleCommand(
            name="status",
            description="System resource status",
            client_method="get_system_resource",
            formatter="format_status_message"
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        client_method: str,
        formatter: str,
        help_emoji: str = ""
    ):
        """Initialize simple command.

        Args:
            name: Command name (e.g., "status")
            description: Human-readable description
            client_method: Method name on MikroTikClient (e.g., "get_system_resource")
            formatter: Function name in formatters module (e.g., "format_status_message")
            help_emoji: Optional emoji for help text
        """
        super().__init__(name, description, client_method, help_emoji)
        self.formatter = formatter

    def register(self, app: Application) -> None:
        """Register command and callback handlers."""
        # Command handler: /status, /interfaces, etc.
        app.add_handler(CommandHandler(self.name, self._create_command_handler()))

        # Callback handler: User clicks device button
        app.add_handler(
            CallbackQueryHandler(
                self._create_callback_handler(),
                pattern=f"^{self.callback_prefix}:.*$"
            )
        )

    def _create_command_handler(self) -> Callable:
        """Create the /command handler."""
        @restricted
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            await update.message.reply_text(
                f"Select a device to view {self.description.lower()}:",
                reply_markup=device_selection_keyboard(self.name)
            )

        # Set function name for better debugging
        handler.__name__ = f"cmd_{self.name}"
        return handler

    def _create_callback_handler(self) -> Callable:
        """Create the callback handler for device selection."""
        @restricted_callback
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            query = update.callback_query
            await query.answer()

            # Parse slug from callback data: "mt:status:router_slug"
            parts = query.data.split(":")
            if len(parts) != 3:
                return
            slug = parts[2]

            # Get client
            client = get_client(slug)
            if not client:
                await query.edit_message_text(f"Device not found: {slug}")
                return

            try:
                # Call client method dynamically
                data = getattr(client, self.client_method)()
                identity = client.get_identity()

                # Call formatter dynamically
                formatter_func = getattr(formatters, self.formatter)
                message = formatter_func(identity, data)

                await query.edit_message_text(message, parse_mode='Markdown')

            except Exception as e:
                logger.error(f"Error in {self.name} for device {slug}: {e}")
                await query.edit_message_text(
                    f"Failed to get {self.description.lower()} for {client.device.name}"
                )

        handler.__name__ = f"callback_{self.name}"
        return handler


class SensitiveCommand(CommandBase):
    """A command that requires MFA and shows a confirmation dialog.

    Perfect for: /reboot, /upgrade, and other destructive operations.

    Example:
        SensitiveCommand(
            name="reboot",
            description="Reboot the router",
            client_method="reboot",
            confirmation_formatter="format_reboot_confirmation_message",
            success_message="✅ Reboot command sent to *{device_name}*"
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        client_method: str,
        confirmation_formatter: str,
        success_message: str,
        help_emoji: str = "🔐"
    ):
        """Initialize sensitive command.

        Args:
            name: Command name (e.g., "reboot")
            description: Human-readable description
            client_method: Method name on MikroTikClient (e.g., "reboot")
            confirmation_formatter: Formatter function for confirmation dialog
            success_message: Message to show on success (can use {device_name})
            help_emoji: Emoji for help text (defaults to 🔐)
        """
        super().__init__(name, description, client_method, help_emoji)
        self.confirmation_formatter = confirmation_formatter
        self.success_message = success_message

    def register(self, app: Application) -> None:
        """Register command and callback handlers with MFA protection."""
        # Command handler: /reboot, /upgrade (with MFA)
        app.add_handler(CommandHandler(self.name, self._create_command_handler()))

        # Callback: Device selection → show confirmation
        app.add_handler(
            CallbackQueryHandler(
                self._create_confirm_handler(),
                pattern=f"^{self.callback_prefix}_confirm:.*$"
            )
        )

        # Callback: User clicked "Yes"
        app.add_handler(
            CallbackQueryHandler(
                self._create_execute_handler(),
                pattern=f"^{self.callback_prefix}_yes:.*$"
            )
        )

        # Callback: User clicked "Cancel"
        app.add_handler(
            CallbackQueryHandler(
                self._create_cancel_handler(),
                pattern=f"^{self.callback_prefix}_no:.*$"
            )
        )

    def _create_command_handler(self) -> Callable:
        """Create the /command handler with MFA."""
        @restricted
        @requires_mfa
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            await update.message.reply_text(
                f"Select a device to {self.description.lower()}:",
                reply_markup=device_selection_keyboard(f"{self.name}_confirm")
            )

        handler.__name__ = f"cmd_{self.name}"
        return handler

    def _create_confirm_handler(self) -> Callable:
        """Create handler to show confirmation dialog."""
        @restricted_callback
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            query = update.callback_query
            await query.answer()

            # Parse slug
            parts = query.data.split(":")
            if len(parts) != 2:
                return
            slug = parts[1]

            # Get client
            client = get_client(slug)
            if not client:
                await query.edit_message_text(f"Device not found: {slug}")
                return

            # Get confirmation message from formatter
            formatter_func = getattr(formatters, self.confirmation_formatter)
            message = formatter_func(client.device.name)

            # Show confirmation keyboard
            keyboard = confirmation_keyboard(self.name, slug)

            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        handler.__name__ = f"callback_{self.name}_confirm"
        return handler

    def _create_execute_handler(self) -> Callable:
        """Create handler to execute the action with MFA recheck."""
        @restricted_callback
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            from .middleware import check_mfa_for_callback

            query = update.callback_query
            await query.answer()

            # Parse slug
            parts = query.data.split(":")
            if len(parts) != 2:
                return
            slug = parts[1]

            # MFA recheck for sensitive action
            action = f"{self.name}_yes"
            mfa_passed = await check_mfa_for_callback(update, context, action)
            if not mfa_passed:
                return

            # Get client
            client = get_client(slug)
            if not client:
                await query.edit_message_text(f"Device not found: {slug}")
                return

            await query.edit_message_text(f"⏳ Processing {self.description.lower()}...")

            try:
                # Execute the action
                getattr(client, self.client_method)()

                # Success message
                message = self.success_message.format(device_name=client.device.name)
                await query.edit_message_text(message, parse_mode='Markdown')

            except Exception as e:
                logger.error(f"Error executing {self.name} on {slug}: {e}")
                await query.edit_message_text(
                    f"❌ Failed to {self.description.lower()} {client.device.name}"
                )

        handler.__name__ = f"callback_{self.name}_execute"
        return handler

    def _create_cancel_handler(self) -> Callable:
        """Create handler for cancellation."""
        @restricted_callback
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text("Operation cancelled.")

        handler.__name__ = f"callback_{self.name}_cancel"
        return handler
