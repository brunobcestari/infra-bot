"""Message formatters for MikroTik bot responses."""

from ..bot.formatters import format_bytes, format_uptime


def format_status_message(identity: str, resource: dict) -> str:
    """Format system status message.

    Args:
        identity: Router identity name
        resource: System resource information from get_system_resource()

    Returns:
        Formatted markdown message
    """
    cpu_load = resource.get('cpu-load', '?')
    free_mem = int(resource.get('free-memory', 0))
    total_mem = int(resource.get('total-memory', 1))
    mem_used = round((1 - free_mem / total_mem) * 100, 1) if total_mem else 0

    free_disk = int(resource.get('free-hdd-space', 0))
    total_disk = int(resource.get('total-hdd-space', 1))
    disk_used = round((1 - free_disk / total_disk) * 100, 1) if total_disk else 0

    return f"""*{identity}* - System Status

*CPU:* {cpu_load}%
*Memory:* {mem_used}% used ({format_bytes(free_mem)} free)
*Disk:* {disk_used}% used ({format_bytes(free_disk)} free)
*Uptime:* {format_uptime(resource.get('uptime', '?'))}

*Board:* {resource.get('board-name', '?')}
*RouterOS:* {resource.get('version', '?')}
*Architecture:* {resource.get('architecture-name', '?')}
"""


def format_interfaces_message(identity: str, interfaces: list[dict]) -> str:
    """Format network interfaces message.

    Args:
        identity: Router identity name
        interfaces: List of interface dictionaries from get_interfaces()

    Returns:
        Formatted markdown message
    """
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

    return "\n".join(lines)


def format_leases_message(identity: str, leases: list[dict]) -> str:
    """Format DHCP leases message.

    Args:
        identity: Router identity name
        leases: List of DHCP lease dictionaries from get_dhcp_leases()

    Returns:
        Formatted markdown message
    """
    if not leases:
        return f"*{identity}*\n\nNo DHCP leases found."

    lines = [f"*{identity}* - DHCP Leases\n"]

    for lease in leases:
        hostname = lease.get('host-name', lease.get('mac-address', '?'))
        ip = lease.get('address', '?')
        status = lease.get('status', '?')
        icon = '✅' if status == 'bound' else '⏳'
        lines.append(f"{icon} *{hostname}*: `{ip}`")

    return "\n".join(lines)


def format_services_message(identity: str, services: list[dict]) -> str:
    """Format enabled IP services message.

    Args:
        identity: Router identity name
        services: List of service dictionaries from get_services_enabled()

    Returns:
        Formatted markdown message
    """
    if not services:
        return f"*{identity}*\n\nNo enabled IP services found."

    lines = [f"*{identity}* - Enabled IP Services\n"]

    for service in services:
        name = service.get('name', '?')
        port = service.get('port', '?')
        protocol = service.get('proto', '?')
        address = service.get('address', '?')
        certificate = service.get('certificate', 'None')
        lines.append(
            f"✅ *{name}*: Port *{port}*, Proto *{protocol}*, "
            f"Address *{address}*, Cert: *{certificate}*"
        )

    return "\n".join(lines)


def format_logs_message(identity: str, logs: list[dict]) -> str:
    """Format log entries message.

    Args:
        identity: Router identity name
        logs: List of log entry dictionaries from get_logs()

    Returns:
        Formatted markdown message
    """
    if not logs:
        return f"*{identity}*\n\nNo log entries found."

    lines = [f"*{identity}* - Recent Logs\n```"]

    for entry in logs:
        time = entry.get('time', '')
        topics = entry.get('topics', '')
        message = entry.get('message', '')
        lines.append(f"{time} [{topics}] {message}")

    lines.append("```")
    return "\n".join(lines)


def format_updates_message(identity: str, update_info: dict) -> str:
    """Format update check message.

    Shows current version, available version, and suggests /upgrade if needed.

    Args:
        identity: Router identity name
        update_info: Update information from check_for_updates()

    Returns:
        Formatted markdown message
    """
    installed = update_info.get('installed-version', '?')
    latest = update_info.get('latest-version', installed)
    channel = update_info.get('channel', '?')

    # Check if update is available
    update_available = installed != latest and latest != installed

    if update_available:
        return f"""*{identity}* - Update Check

🆕 *Update Available!*

*Installed:* {installed}
*Available:* {latest}
*Channel:* {channel}

To install the update, use /upgrade command.
"""
    else:
        return f"""*{identity}* - Update Check

✅ *Running the latest version*

*Installed:* {installed}
*Channel:* {channel}
"""


# Deprecated: kept for backward compatibility with existing code
def format_update_current_message(identity: str, update_info: dict) -> str:
    """Deprecated: Use format_updates_message instead."""
    return format_updates_message(identity, update_info)


def format_update_available_message(identity: str, update_info: dict) -> str:
    """Deprecated: Use format_updates_message instead."""
    return format_updates_message(identity, update_info)


def format_upgrade_confirmation_message(device_name: str) -> str:
    """Format upgrade confirmation message.

    Args:
        device_name: Name of the device to upgrade

    Returns:
        Formatted markdown message
    """
    return (
        f"⚠️ *Upgrade {device_name}?*\n\n"
        "This will download and install the latest update. "
        "The router will reboot automatically.\n\n"
        "Are you sure?"
    )


def format_reboot_confirmation_message(device_name: str) -> str:
    """Format reboot confirmation message.

    Args:
        device_name: Name of the device to reboot

    Returns:
        Formatted markdown message
    """
    return (
        f"⚠️ *Reboot {device_name}?*\n\n"
        "This will immediately reboot the router. "
        "All active connections will be dropped.\n\n"
        "Are you sure?"
    )
