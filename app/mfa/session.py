"""Session management for MFA with in-memory cache."""

import logging
from datetime import datetime
from typing import Optional

from .database import MFADatabase

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages MFA sessions with in-memory cache + database persistence."""

    def __init__(self, db: MFADatabase, default_duration: int = 15):
        """Initialize session manager.

        Args:
            db: MFA database instance
            default_duration: Default session duration in minutes
        """
        self.db = db
        self.default_duration = default_duration
        # In-memory cache: user_id -> session_id
        self._cache: dict[int, str] = {}

    def create_session(self, user_id: int) -> str:
        """Create a new MFA session.

        Invalidates any existing session for this user.

        Args:
            user_id: Telegram user ID

        Returns:
            Session ID (UUID)
        """
        # Invalidate any existing session
        if user_id in self._cache:
            old_session_id = self._cache[user_id]
            self.db.invalidate_session(old_session_id)
            logger.debug(f"Invalidated previous session for user {user_id}")

        # Create new session
        session_id = self.db.create_session(user_id, self.default_duration)
        self._cache[user_id] = session_id

        logger.info(f"Created MFA session for user {user_id} (duration: {self.default_duration}min)")
        return session_id

    def has_valid_session(self, user_id: int) -> bool:
        """Check if user has a valid (non-expired) session.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user has an active session
        """
        # Check cache first
        if user_id in self._cache:
            session_id = self._cache[user_id]
            session = self.db.get_session(session_id)

            if session:
                # Check if session is expired
                expires_at = datetime.fromisoformat(session['expires_at'])
                if expires_at > datetime.utcnow():
                    logger.debug(f"User {user_id} has valid cached session")
                    return True
                else:
                    # Session expired, clean up cache
                    logger.debug(f"User {user_id} cached session expired")
                    del self._cache[user_id]
            else:
                # Session not found in DB, clean up cache
                del self._cache[user_id]

        # Fallback to database check (in case cache was cleared)
        session_id = self.db.get_user_session(user_id)
        if session_id:
            # Update cache
            self._cache[user_id] = session_id
            logger.debug(f"User {user_id} has valid session (recovered from DB)")
            return True

        return False

    def invalidate_user_session(self, user_id: int) -> None:
        """Invalidate user's session.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self._cache:
            session_id = self._cache[user_id]
            self.db.invalidate_session(session_id)
            del self._cache[user_id]
            logger.info(f"Invalidated session for user {user_id}")
        else:
            # Check DB in case cache was cleared
            session_id = self.db.get_user_session(user_id)
            if session_id:
                self.db.invalidate_session(session_id)
                logger.info(f"Invalidated session for user {user_id} (from DB)")

    def cleanup_expired(self) -> None:
        """Remove expired sessions from database.

        This should be called periodically (e.g., every 5 minutes).
        """
        count = self.db.cleanup_expired_sessions()

        # Clear cache for safety after cleanup
        # (Alternatively, we could be smarter and only remove expired entries)
        if count > 0:
            self._cache.clear()
            logger.debug(f"Cleaned up {count} expired sessions, cleared cache")

    def get_session_info(self, user_id: int) -> Optional[dict]:
        """Get session information for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Session info dictionary or None if no session
        """
        session_id = self._cache.get(user_id) or self.db.get_user_session(user_id)
        if session_id:
            return self.db.get_session(session_id)
        return None
