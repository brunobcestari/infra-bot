"""Internal framework modules for MikroTik bot.

These are framework files that developers rarely need to edit.
When adding new commands, you only need to edit the files in the parent directory.
"""

from .command_base import SimpleCommand, SensitiveCommand
from .registration import register_handlers

__all__ = ["SimpleCommand", "SensitiveCommand", "register_handlers"]
