"""MFA module for Telegram infrastructure bot."""

import logging
from pathlib import Path
from typing import Tuple

from .database import MFADatabase
from .session import SessionManager
from .decorators import init_mfa_decorators, requires_mfa, requires_mfa_callback
from .handlers import register_mfa_handlers

logger = logging.getLogger(__name__)

# Module-level instances
_mfa_db: MFADatabase | None = None
_session_manager: SessionManager | None = None


def initialize_mfa_system(
    db_path: Path,
    encryption_key: bytes,
    session_duration: int
) -> Tuple[MFADatabase, SessionManager]:
    """Initialize the MFA system.

    Creates database, session manager, and initializes decorators.

    Args:
        db_path: Path to SQLite database file
        encryption_key: Master encryption key for TOTP secrets
        session_duration: Default session duration in minutes

    Returns:
        Tuple of (MFADatabase, SessionManager)
    """
    global _mfa_db, _session_manager

    logger.info(f"Initializing MFA system (db: {db_path}, session: {session_duration}min)")

    # Create database
    _mfa_db = MFADatabase(db_path=db_path, encryption_key=encryption_key)

    # Create session manager
    _session_manager = SessionManager(db=_mfa_db, default_duration=session_duration)

    # Initialize decorators with instances
    init_mfa_decorators(session_manager=_session_manager, mfa_db=_mfa_db)

    logger.info("MFA system initialized successfully")

    return _mfa_db, _session_manager


def get_session_manager() -> SessionManager | None:
    """Get the global session manager instance.

    Returns:
        SessionManager instance or None if not initialized
    """
    return _session_manager


def get_mfa_database() -> MFADatabase | None:
    """Get the global MFA database instance.

    Returns:
        MFADatabase instance or None if not initialized
    """
    return _mfa_db


# Public API
__all__ = [
    'initialize_mfa_system',
    'register_mfa_handlers',
    'requires_mfa',
    'requires_mfa_callback',
    'get_session_manager',
    'get_mfa_database',
    'MFADatabase',
    'SessionManager',
]
