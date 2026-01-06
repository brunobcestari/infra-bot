"""Formatting utilities for human-readable output."""


def format_uptime(seconds: str) -> str:
    """Format uptime from seconds to human readable (e.g., '2d 5h 30m')."""
    try:
        # RouterOS returns uptime like "1w2d3h4m5s" or just seconds
        if any(c.isalpha() for c in seconds):
            return seconds  # Already formatted

        total_seconds = int(seconds.rstrip('s'))
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if secs or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)
    except (ValueError, AttributeError):
        return str(seconds)


def format_bytes(value: str | int) -> str:
    """Format bytes to human readable (e.g., '1.5 GB')."""
    try:
        bytes_val = int(value) if isinstance(value, str) else value
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                if unit == 'B':
                    return f"{bytes_val} {unit}"
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(used: int, total: int) -> float:
    """Calculate percentage used."""
    if total == 0:
        return 0.0
    return round((1 - used / total) * 100, 1)


def truncate(text: str, max_length: int = 4096) -> str:
    """Truncate text to fit Telegram message limits."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
