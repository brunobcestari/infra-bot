"""Logging configuration with environment variable support."""

import logging
import os

# Default log level
DEFAULT_LOG_LEVEL = "INFO"

# Valid log levels
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

_logging_configured = False


def get_log_level() -> int:
    """Get log level from LOG_LEVEL environment variable.
    
    Returns:
        Logging level constant (e.g., logging.INFO)
    """
    level_str = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    
    if level_str not in VALID_LEVELS:
        level_str = DEFAULT_LOG_LEVEL
    
    return getattr(logging, level_str)


def setup_logging() -> None:
    """Setup logging configuration for the application.
    
    Configures the root logger with format and level from environment.
    Should be called once at application startup.
    """
    global _logging_configured
    if _logging_configured:
        return
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=get_log_level()
    )
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name.
    
    Ensures logging is configured before returning the logger.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    setup_logging()
    return logging.getLogger(name)