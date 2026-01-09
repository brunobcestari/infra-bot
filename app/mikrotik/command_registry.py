"""Command registry - Define all MikroTik commands here!

This is the ONLY place you need to add new commands.
Just instantiate SimpleCommand or SensitiveCommand with the right parameters!
"""

from telegram.ext import Application

from ._internal import SimpleCommand, SensitiveCommand


# ========================================
# Simple Read Commands
# ========================================

SIMPLE_COMMANDS = [
    SimpleCommand(
        name="status",
        description="System resource status",
        client_method="get_system_resource",
        formatter="format_status_message",
        allow_readonly=True
    ),

    SimpleCommand(
        name="interfaces",
        description="Network interfaces",
        client_method="get_interfaces",
        formatter="format_interfaces_message",
        allow_readonly=True
    ),

    SimpleCommand(
        name="leases",
        description="DHCP leases",
        client_method="get_dhcp_leases",
        formatter="format_leases_message",
        allow_readonly=True
    ),

    SimpleCommand(
        name="logs",
        description="Recent log entries",
        client_method="get_logs",
        formatter="format_logs_message",
        allow_readonly=True
    ),

    SimpleCommand(
        name="services_enabled",
        description="Enabled IP services",
        client_method="get_services_enabled",
        formatter="format_services_message",
        allow_readonly=True
    ),

    SimpleCommand(
        name="updates",
        description="Check for RouterOS updates",
        client_method="check_for_updates",
        formatter="format_updates_message",
        allow_readonly=True
    ),
]


# ========================================
# Sensitive Commands (require MFA)
# ========================================

SENSITIVE_COMMANDS = [
    SensitiveCommand(
        name="reboot",
        description="Reboot the router",
        client_method="reboot",
        confirmation_formatter="format_reboot_confirmation_message",
        success_message="✅ Reboot command sent to *{device_name}*"
    ),

    SensitiveCommand(
        name="upgrade",
        description="Install RouterOS updates",
        client_method="install_updates",
        confirmation_formatter="format_upgrade_confirmation_message",
        success_message="✅ Upgrade started on *{device_name}*. Router will reboot."
    ),
]


# ========================================
# Registration
# ========================================

def register_all_commands(app: Application) -> None:
    """Register all commands with the bot application.

    This automatically:
    - Registers all command handlers (/status, /reboot, etc.)
    - Registers all callback handlers (button clicks)
    - Applies MFA protection to sensitive commands
    - Updates SENSITIVE_ACTIONS list for middleware
    """
    # Register simple commands
    for cmd in SIMPLE_COMMANDS:
        cmd.register(app)

    # Register sensitive commands
    for cmd in SENSITIVE_COMMANDS:
        cmd.register(app)

    # Auto-update SENSITIVE_ACTIONS in middleware
    _update_sensitive_actions()


def _update_sensitive_actions() -> None:
    """Automatically update SENSITIVE_ACTIONS in middleware based on registered commands."""
    from ._internal import middleware

    # Build set of sensitive actions from registered commands
    sensitive_actions = {
        f"{cmd.name}_yes"  # Only the actual execution, not _confirm
        for cmd in SENSITIVE_COMMANDS
    }

    # Update middleware
    middleware.SENSITIVE_ACTIONS = sensitive_actions


def get_help_text(is_admin: bool = True) -> str:
    """Generate help text for all commands.
    
    Args:
        is_admin: If True, show all commands. If False, only show readonly commands.

    Returns:
        Formatted markdown help text
    """
    lines = ["*MikroTik Management Bot*\n"]

    # System commands - filter for readonly users
    if SIMPLE_COMMANDS:
        visible_commands = [cmd for cmd in SIMPLE_COMMANDS if is_admin or cmd.allow_readonly]
        if visible_commands:
            lines.append("*System Commands:*")
            for cmd in visible_commands:
                lines.append(cmd.get_help_text())
            lines.append("")

    # Maintenance commands - only for admins
    if is_admin and SENSITIVE_COMMANDS:
        lines.append("*Maintenance:*")
        for cmd in SENSITIVE_COMMANDS:
            lines.append(cmd.get_help_text())
        lines.append("")

    # Footer
    if is_admin:
        lines.extend([
            "*Security:*",
            "/mfa\\_auth - Authenticate and create MFA session",
            "/mfa\\_status - Check MFA enrollment status",
            "",
            "/help - Show this message",
            "",
            "_🔐 Requires MFA authentication_"
        ])
    else:
        lines.extend([
            "/help - Show this message"
        ])

    return "\n".join(lines)
