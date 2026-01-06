"""Telegram bot for infrastructure management."""

import logging

from .bot import create_bot
from .mikrotik import register_handlers as register_mikrotik_handlers
from .mfa import initialize_mfa_system, register_mfa_handlers, get_session_manager
from .config import get_config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def periodic_cleanup(context) -> None:
    """Periodic task to cleanup expired MFA sessions."""
    session_manager = get_session_manager()
    if session_manager:
        session_manager.cleanup_expired()


def main() -> None:
    """Run the bot."""
    logger.info("Starting bot...")

    config = get_config()
    app = create_bot()

    # Initialize MFA system if enabled
    if config.mfa_enabled:
        logger.info("Initializing MFA system...")
        mfa_db, session_manager = initialize_mfa_system(
            db_path=config.mfa_db_path,
            encryption_key=config.mfa_encryption_key,
            session_duration=config.mfa_session_duration
        )
        register_mfa_handlers(app, mfa_db, session_manager)

        # Schedule periodic cleanup every 5 minutes
        app.job_queue.run_repeating(
            periodic_cleanup,
            interval=300,  # 5 minutes
            first=60       # Start after 1 minute
        )
        logger.info("MFA system initialized")
    else:
        logger.warning("MFA is disabled in configuration")

    # Register handlers for each device type
    register_mikrotik_handlers(app)
    # Future: register_unifi_handlers(app)
    # Future: register_proxmox_handlers(app)

    logger.info("Bot started. Polling for updates...")
    app.run_polling()


if __name__ == '__main__':
    main()
