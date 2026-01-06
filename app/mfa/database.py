"""SQLite database for MFA user data and sessions."""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .encryption import EncryptionHelper

logger = logging.getLogger(__name__)


class MFADatabase:
    """SQLite database manager for MFA users and sessions."""

    def __init__(self, db_path: Path, encryption_key: bytes):
        """Initialize MFA database.

        Args:
            db_path: Path to SQLite database file
            encryption_key: Master encryption key for secret encryption
        """
        self.db_path = db_path
        self.encryption = EncryptionHelper(encryption_key)

        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        self._cleanup_expired_sessions()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users_mfa (
                    user_id INTEGER PRIMARY KEY,
                    totp_secret TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    backup_codes TEXT,
                    failed_attempts INTEGER DEFAULT 0,
                    last_failed_attempt TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS mfa_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users_mfa(user_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS mfa_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON mfa_sessions(user_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
                ON mfa_sessions(expires_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp
                ON mfa_audit_log(user_id, timestamp)
            """)

            conn.commit()

    # User MFA Management

    def enroll_user(self, user_id: int, totp_secret: str) -> None:
        """Enroll user in MFA system.

        Args:
            user_id: Telegram user ID
            totp_secret: Base32 TOTP secret (will be encrypted)
        """
        encrypted_secret = self.encryption.encrypt(totp_secret)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users_mfa
                (user_id, totp_secret, created_at, is_active, failed_attempts)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1, 0)
            """, (user_id, encrypted_secret))
            conn.commit()

        self.log_event(user_id, 'enrollment', {'method': 'totp'})
        logger.info(f"User {user_id} enrolled in MFA")

    def get_user_secret(self, user_id: int) -> Optional[str]:
        """Get decrypted TOTP secret for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Decrypted TOTP secret or None if not enrolled
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT totp_secret FROM users_mfa
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            row = cursor.fetchone()

        if row:
            return self.encryption.decrypt(row[0])
        return None

    def is_user_enrolled(self, user_id: int) -> bool:
        """Check if user is enrolled in MFA.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is enrolled and active
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM users_mfa
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            return cursor.fetchone() is not None

    def get_user_info(self, user_id: int) -> Optional[dict]:
        """Get user MFA information.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with user info or None if not enrolled
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_id, created_at, last_used_at, is_active
                FROM users_mfa
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def disable_user_mfa(self, user_id: int) -> None:
        """Disable user's MFA (soft delete).

        Args:
            user_id: Telegram user ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users_mfa
                SET is_active = 0
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

        # Invalidate all sessions
        self._invalidate_all_user_sessions(user_id)

        self.log_event(user_id, 'mfa_disabled', {})
        logger.info(f"User {user_id} MFA disabled")

    def list_enrolled_users(self) -> list[dict]:
        """List all enrolled users.

        Returns:
            List of user info dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_id, created_at, last_used_at, is_active
                FROM users_mfa
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_last_used(self, user_id: int) -> None:
        """Update last used timestamp for user.

        Args:
            user_id: Telegram user ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users_mfa
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    # Session Management

    def create_session(self, user_id: int, duration_minutes: int) -> str:
        """Create a new MFA session.

        Args:
            user_id: Telegram user ID
            duration_minutes: Session duration in minutes

        Returns:
            Session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO mfa_sessions (session_id, user_id, expires_at)
                VALUES (?, ?, ?)
            """, (session_id, user_id, expires_at.isoformat()))
            conn.commit()

        self.log_event(user_id, 'session_created', {'session_id': session_id, 'duration_minutes': duration_minutes})
        logger.debug(f"Created session {session_id} for user {user_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session information.

        Args:
            session_id: Session UUID

        Returns:
            Session dictionary or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT session_id, user_id, created_at, expires_at, last_activity
                FROM mfa_sessions
                WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_user_session(self, user_id: int) -> Optional[str]:
        """Get active session ID for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Session ID or None if no valid session
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_id FROM mfa_sessions
                WHERE user_id = ? AND expires_at > ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id, datetime.utcnow().isoformat()))
            row = cursor.fetchone()

        return row[0] if row else None

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session.

        Args:
            session_id: Session UUID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM mfa_sessions
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()

        logger.debug(f"Invalidated session {session_id}")

    def _invalidate_all_user_sessions(self, user_id: int) -> None:
        """Invalidate all sessions for a user.

        Args:
            user_id: Telegram user ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM mfa_sessions
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from database.

        Returns:
            Number of sessions removed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM mfa_sessions
                WHERE expires_at < ?
            """, (datetime.utcnow().isoformat(),))
            conn.commit()
            count = cursor.rowcount

        if count > 0:
            logger.debug(f"Cleaned up {count} expired sessions")
        return count

    def _cleanup_expired_sessions(self) -> None:
        """Internal cleanup called on initialization."""
        self.cleanup_expired_sessions()

    # Rate Limiting

    def is_rate_limited(self, user_id: int, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if user is rate limited due to failed attempts.

        Args:
            user_id: Telegram user ID
            max_attempts: Maximum failed attempts allowed
            window_minutes: Time window for rate limiting

        Returns:
            True if user is rate limited
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT failed_attempts, last_failed_attempt
                FROM users_mfa
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

        if not row:
            return False

        failed_attempts, last_failed = row

        if failed_attempts < max_attempts:
            return False

        if last_failed:
            last_failed_time = datetime.fromisoformat(last_failed)
            window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

            if last_failed_time < window_start:
                # Window expired, reset counter
                self.reset_failed_attempts(user_id)
                return False

        return True

    def increment_failed_attempts(self, user_id: int) -> int:
        """Increment failed attempt counter.

        Args:
            user_id: Telegram user ID

        Returns:
            New failed attempt count
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users_mfa
                SET failed_attempts = failed_attempts + 1,
                    last_failed_attempt = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

            cursor = conn.execute("""
                SELECT failed_attempts FROM users_mfa
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

        count = row[0] if row else 0
        logger.warning(f"User {user_id} failed MFA attempt #{count}")
        return count

    def reset_failed_attempts(self, user_id: int) -> None:
        """Reset failed attempt counter.

        Args:
            user_id: Telegram user ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users_mfa
                SET failed_attempts = 0,
                    last_failed_attempt = NULL
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    # Audit Logging

    def log_event(self, user_id: int, event_type: str, details: Optional[dict] = None) -> None:
        """Log MFA event to audit log.

        Args:
            user_id: Telegram user ID
            event_type: Type of event (enrollment, verification_success, etc.)
            details: Optional dictionary with additional details
        """
        details_json = json.dumps(details) if details else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO mfa_audit_log (user_id, event_type, details)
                VALUES (?, ?, ?)
            """, (user_id, event_type, details_json))
            conn.commit()
