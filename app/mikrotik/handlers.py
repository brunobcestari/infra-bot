"""MikroTik bot command handlers with multi-device support."""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from ..bot.decorators import restricted, restricted_callback
from ..bot.formatters import format_bytes, format_uptime
from ..config import get_config
from .client import get_client, MikroTikClient

logger = logging.getLogger(__name__)

# Callback data prefixes
CB_PREFIX = "mt"  # mikrotik


def _device_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create inline keyboard with device selection."""
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


def _parse_callback(data: str) -> tuple[str, str] | None:
    """Parse callback data into (action, slug)."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CB_PREFIX:
        return None
    return parts[1], parts[2]


async def _handle_device_action(
    query,
    slug: str,
    action_func,
    error_msg: str = "Operation failed."
) -> None:
    """Generic handler for device actions."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    try:
        result = await action_func(client)
        await query.edit_message_text(result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"MikroTik error ({slug}): {e}")
        await query.edit_message_text(f"{error_msg}\n\nDevice: {client.device.name}")


# --- Command Handlers ---

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message with available commands."""
    help_text = """
*MikroTik Management Bot*

*System Commands:*
/status - System resource status
/interfaces - Network interfaces
/leases - DHCP leases
/logs - Recent log entries

*Maintenance:*
/updates - Check for RouterOS updates
/upgrade - Install available updates
/reboot - Reboot the router

/help - Show this message
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


@restricted
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for status command."""
    await update.message.reply_text(
        "Select a device to view status:",
        reply_markup=_device_keyboard("status")
    )


@restricted
async def cmd_interfaces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for interfaces command."""
    await update.message.reply_text(
        "Select a device to view interfaces:",
        reply_markup=_device_keyboard("interfaces")
    )


@restricted
async def cmd_leases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for DHCP leases command."""
    await update.message.reply_text(
        "Select a device to view DHCP leases:",
        reply_markup=_device_keyboard("leases")
    )


@restricted
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for logs command."""
    await update.message.reply_text(
        "Select a device to view logs:",
        reply_markup=_device_keyboard("logs")
    )


@restricted
async def cmd_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for update check."""
    await update.message.reply_text(
        "Select a device to check for updates:",
        reply_markup=_device_keyboard("updates")
    )


@restricted
async def cmd_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for upgrade."""
    await update.message.reply_text(
        "Select a device to upgrade:",
        reply_markup=_device_keyboard("upgrade_confirm")
    )


@restricted
async def cmd_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show device selector for reboot."""
    await update.message.reply_text(
        "Select a device to reboot:",
        reply_markup=_device_keyboard("reboot_confirm")
    )


# --- Callback Handlers ---

@restricted_callback
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all MikroTik callback queries."""
    query = update.callback_query
    await query.answer()

    parsed = _parse_callback(query.data)
    if parsed is None:
        return

    action, slug = parsed

    handlers = {
        "status": _handle_status,
        "interfaces": _handle_interfaces,
        "leases": _handle_leases,
        "logs": _handle_logs,
        "updates": _handle_updates,
        "upgrade_confirm": _handle_upgrade_confirm,
        "upgrade_yes": _handle_upgrade_yes,
        "upgrade_no": _handle_cancel,
        "reboot_confirm": _handle_reboot_confirm,
        "reboot_yes": _handle_reboot_yes,
        "reboot_no": _handle_cancel,
    }

    handler = handlers.get(action)
    if handler:
        await handler(query, slug)


async def _handle_status(query, slug: str) -> None:
    """Handle status callback."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    try:
        res = client.get_system_resource()
        identity = client.get_identity()

        cpu_load = res.get('cpu-load', '?')
        free_mem = int(res.get('free-memory', 0))
        total_mem = int(res.get('total-memory', 1))
        mem_used = round((1 - free_mem / total_mem) * 100, 1) if total_mem else 0

        free_disk = int(res.get('free-hdd-space', 0))
        total_disk = int(res.get('total-hdd-space', 1))
        disk_used = round((1 - free_disk / total_disk) * 100, 1) if total_disk else 0

        msg = f"""
*{identity}* - System Status

*CPU:* {cpu_load}%
*Memory:* {mem_used}% used ({format_bytes(free_mem)} free)
*Disk:* {disk_used}% used ({format_bytes(free_disk)} free)
*Uptime:* {format_uptime(res.get('uptime', '?'))}

*Board:* {res.get('board-name', '?')}
*RouterOS:* {res.get('version', '?')}
*Architecture:* {res.get('architecture-name', '?')}
"""
        await query.edit_message_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Status error ({slug}): {e}")
        await query.edit_message_text(f"Failed to get status for {client.device.name}")


async def _handle_interfaces(query, slug: str) -> None:
    """Handle interfaces callback."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    try:
        interfaces = client.get_interfaces()
        identity = client.get_identity()

        lines = [f"*{identity}* - Network Interfaces\n"]
        for iface in interfaces:
            name = iface.get('name', '?')
            iface_type = iface.get('type', '?')
            running = '✅' if iface.get('running') == 'true' else '❌'
            disabled = ' (disabled)' if iface.get('disabled') == 'true' else ''

            tx = format_bytes(iface.get('tx-byte', '0'))
            rx = format_bytes(iface.get('rx-byte', '0'))

            lines.append(f"{running} *{name}*{disabled}")
            lines.append(f"    {iface_type} | TX: {tx} | RX: {rx}")

        await query.edit_message_text("\n".join(lines), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Interfaces error ({slug}): {e}")
        await query.edit_message_text(f"Failed to get interfaces for {client.device.name}")


async def _handle_leases(query, slug: str) -> None:
    """Handle DHCP leases callback."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    try:
        leases = client.get_dhcp_leases()
        identity = client.get_identity()

        if not leases:
            await query.edit_message_text(f"*{identity}*\n\nNo DHCP leases found.", parse_mode='Markdown')
            return

        lines = [f"*{identity}* - DHCP Leases\n"]
        for lease in leases:
            hostname = lease.get('host-name', lease.get('mac-address', '?'))
            ip = lease.get('address', '?')
            status = lease.get('status', '?')
            icon = '✅' if status == 'bound' else '⏳'
            lines.append(f"{icon} *{hostname}*: `{ip}`")

        await query.edit_message_text("\n".join(lines), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Leases error ({slug}): {e}")
        await query.edit_message_text(f"Failed to get DHCP leases for {client.device.name}")


async def _handle_logs(query, slug: str) -> None:
    """Handle logs callback."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    try:
        logs = client.get_logs(15)
        identity = client.get_identity()

        if not logs:
            await query.edit_message_text(f"*{identity}*\n\nNo log entries found.", parse_mode='Markdown')
            return

        lines = [f"*{identity}* - Recent Logs\n```"]
        for entry in logs:
            time = entry.get('time', '')
            topics = entry.get('topics', '')
            message = entry.get('message', '')
            lines.append(f"{time} [{topics}] {message}")
        lines.append("```")

        await query.edit_message_text("\n".join(lines), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Logs error ({slug}): {e}")
        await query.edit_message_text(f"Failed to get logs for {client.device.name}")


async def _handle_updates(query, slug: str) -> None:
    """Handle update check callback."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    await query.edit_message_text(f"Checking for updates on {client.device.name}...")

    try:
        result = client.check_for_updates()
        identity = client.get_identity()

        installed = result.get('installed-version', '?')
        latest = result.get('latest-version', installed)
        channel = result.get('channel', '?')

        if installed == latest:
            msg = f"""
*{identity}* - Update Check

✅ Running the latest version

*Installed:* {installed}
*Channel:* {channel}
"""
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            msg = f"""
*{identity}* - Update Check

🆕 Update available!

*Installed:* {installed}
*Available:* {latest}
*Channel:* {channel}
"""
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⬆️ Install Update", callback_data=f"{CB_PREFIX}:upgrade_yes:{slug}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"{CB_PREFIX}:upgrade_no:{slug}"),
                ]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Updates error ({slug}): {e}")
        await query.edit_message_text(f"Failed to check updates for {client.device.name}")


async def _handle_upgrade_confirm(query, slug: str) -> None:
    """Show upgrade confirmation."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, upgrade", callback_data=f"{CB_PREFIX}:upgrade_yes:{slug}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"{CB_PREFIX}:upgrade_no:{slug}"),
        ]
    ])

    await query.edit_message_text(
        f"⚠️ *Upgrade {client.device.name}?*\n\n"
        "This will download and install the latest update. "
        "The router will reboot automatically.\n\n"
        "Are you sure?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def _handle_upgrade_yes(query, slug: str) -> None:
    """Execute upgrade."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    await query.edit_message_text(f"⏳ Starting upgrade on {client.device.name}...")

    try:
        client.install_updates()
        await query.edit_message_text(f"✅ Upgrade started on *{client.device.name}*. Router will reboot.", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Upgrade error ({slug}): {e}")
        await query.edit_message_text(f"❌ Failed to upgrade {client.device.name}")


async def _handle_reboot_confirm(query, slug: str) -> None:
    """Show reboot confirmation."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, reboot", callback_data=f"{CB_PREFIX}:reboot_yes:{slug}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"{CB_PREFIX}:reboot_no:{slug}"),
        ]
    ])

    await query.edit_message_text(
        f"⚠️ *Reboot {client.device.name}?*\n\n"
        "This will immediately reboot the router. "
        "All active connections will be dropped.\n\n"
        "Are you sure?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def _handle_reboot_yes(query, slug: str) -> None:
    """Execute reboot."""
    client = get_client(slug)
    if client is None:
        await query.edit_message_text(f"Device not found: {slug}")
        return

    await query.edit_message_text(f"⏳ Rebooting {client.device.name}...")

    try:
        client.reboot()
        await query.edit_message_text(f"✅ Reboot command sent to *{client.device.name}*", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Reboot error ({slug}): {e}")
        await query.edit_message_text(f"❌ Failed to reboot {client.device.name}")


async def _handle_cancel(query, slug: str) -> None:
    """Handle cancellation."""
    await query.edit_message_text("Operation cancelled.")


def register_handlers(app: Application) -> None:
    """Register all MikroTik handlers with the bot."""
    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("interfaces", cmd_interfaces))
    app.add_handler(CommandHandler("leases", cmd_leases))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("updates", cmd_updates))
    app.add_handler(CommandHandler("upgrade", cmd_upgrade))
    app.add_handler(CommandHandler("reboot", cmd_reboot))

    # Callbacks (all MikroTik callbacks start with "mt:")
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=f"^{CB_PREFIX}:"))
