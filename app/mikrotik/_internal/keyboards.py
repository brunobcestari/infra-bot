"""Inline keyboard builders for MikroTik bot commands."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...config import get_config

# Callback data prefix for MikroTik commands
CB_PREFIX = "mt"


def device_selection_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create inline keyboard with device selection buttons.

    Args:
        action: The action to perform (e.g., 'status', 'reboot')

    Returns:
        InlineKeyboardMarkup with device selection buttons arranged in rows of 2
    """
    config = get_config()
    buttons = [
        InlineKeyboardButton(
            device.name,
            callback_data=f"{CB_PREFIX}:{action}:{device.slug}"
        )
        for device in config.mikrotik_devices
    ]
    # Arrange in rows of 2
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def confirmation_keyboard(action: str, slug: str) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for destructive actions.

    Args:
        action: The action to confirm (e.g., 'upgrade', 'reboot')
        slug: The device slug

    Returns:
        InlineKeyboardMarkup with Yes/No buttons
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"✅ Yes, {action}",
                callback_data=f"{CB_PREFIX}:{action}_yes:{slug}"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data=f"{CB_PREFIX}:{action}_no:{slug}"
            ),
        ]
    ])


def upgrade_available_keyboard(slug: str) -> InlineKeyboardMarkup:
    """Create keyboard for when an update is available.

    Args:
        slug: The device slug

    Returns:
        InlineKeyboardMarkup with Install/Cancel buttons
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬆️ Install Update",
                callback_data=f"{CB_PREFIX}:upgrade_yes:{slug}"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data=f"{CB_PREFIX}:upgrade_no:{slug}"
            ),
        ]
    ])


def parse_callback_data(data: str) -> tuple[str, str] | None:
    """Parse callback data into (action, slug).

    Args:
        data: Callback data string in format "prefix:action:slug"

    Returns:
        Tuple of (action, slug) or None if invalid format
    """
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CB_PREFIX:
        return None
    return parts[1], parts[2]
