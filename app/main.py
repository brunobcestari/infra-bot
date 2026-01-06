"""Telegram bot for infrastructure management."""

import logging

from .bot import create_bot
from .mikrotik import register_handlers as register_mikrotik_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    """Run the bot."""
    logger.info("Starting bot...")

    app = create_bot()

    # Register handlers for each device type
    register_mikrotik_handlers(app)
    # Future: register_unifi_handlers(app)
    # Future: register_proxmox_handlers(app)

    logger.info("Bot started. Polling for updates...")
    app.run_polling()


if __name__ == '__main__':
    main()
