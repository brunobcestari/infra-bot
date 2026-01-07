import json
import os
import re
from pathlib import Path
from dataclasses import dataclass

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


@dataclass(frozen=True)
class MikroTikDevice:
    """MikroTik device configuration."""
    name: str
    slug: str
    host: str
    port: int
    username: str
    password: str
    ssl_cert: Path


@dataclass(frozen=True)
class Config:
    """Application configuration."""
    telegram_token: str
    admin_ids: frozenset[int]
    mikrotik_devices: tuple[MikroTikDevice, ...]

    # MFA configuration
    mfa_enabled: bool = True
    mfa_session_duration: int = 15
    mfa_db_path: Path = Path("/data/mfa.db")
    mfa_encryption_key: bytes | None = None

    def get_mikrotik_device(self, slug: str) -> MikroTikDevice | None:
        """Get a MikroTik device by its slug."""
        for device in self.mikrotik_devices:
            if device.slug == slug:
                return device
        return None


def _slugify(name: str) -> str:
    """Convert device name to a URL/callback-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


def _get_env(name: str, required: bool = True) -> str:
    """Get environment variable."""
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


def load_config() -> Config:
    """Load configuration from config.json and environment variables."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as f:
        data = json.load(f)

    # Telegram config
    telegram_token = _get_env("TELEGRAM_BOT_TOKEN")
    admin_ids = frozenset(data.get("telegram", {}).get("admin_ids", []))

    if not admin_ids:
        raise ValueError("No admin_ids configured in config.json")

    # MikroTik devices
    mikrotik_devices = []
    base_path = Path(__file__).parent

    for device_data in data.get("devices", {}).get("mikrotik", []):
        name = device_data["name"]
        slug = _slugify(name)

        # Password from environment variable: MIKROTIK_<SLUG>_PASSWORD
        env_key = f"MIKROTIK_{slug.upper()}_PASSWORD"
        password = _get_env(env_key)

        # SSL cert path - supports multiple formats:
        # - Omitted: defaults to {slug}.crt (e.g., "main_router.crt")
        # - Filename only: "my_cert.crt" → /app/certs/my_cert.crt
        # - Relative path: "certs/my_cert.crt" → /app/certs/my_cert.crt
        # - Absolute path: "/custom/path/cert.crt" → /custom/path/cert.crt
        ssl_cert_path = device_data.get("ssl_cert", f"{slug}.crt")

        if ssl_cert_path.startswith('/'):
            # Absolute path - use as-is
            ssl_cert = Path(ssl_cert_path)
        elif '/' in ssl_cert_path:
            # Relative path with directory - relative to app/
            ssl_cert = base_path / ssl_cert_path
        else:
            # Just a filename - assume it's in /app/certs/
            ssl_cert = Path("/app/certs") / ssl_cert_path

        if not ssl_cert.exists():
            raise FileNotFoundError(f"SSL certificate not found for {name}: {ssl_cert}")

        device = MikroTikDevice(
            name=name,
            slug=slug,
            host=device_data["host"],
            port=device_data.get("port", 8729),
            username=device_data["username"],
            password=password,
            ssl_cert=ssl_cert,
        )
        mikrotik_devices.append(device)

    if not mikrotik_devices:
        raise ValueError("No MikroTik devices configured in config.json")

    # MFA configuration
    mfa_config = data.get("mfa", {})
    mfa_enabled = mfa_config.get("enabled", True)
    mfa_session_duration = mfa_config.get("session_duration_minutes", 15)

    # MFA database path (default to /data/mfa.db for Docker volume)
    mfa_db_path_str = mfa_config.get("db_path", "/data/mfa.db")
    mfa_db_path = Path(mfa_db_path_str)

    # MFA encryption key from environment
    mfa_encryption_key = None
    if mfa_enabled:
        mfa_key_str = os.getenv("MFA_ENCRYPTION_KEY")
        if not mfa_key_str:
            raise ValueError(
                "MFA_ENCRYPTION_KEY environment variable required when MFA is enabled. "
                "Generate with: openssl rand -base64 32"
            )
        mfa_encryption_key = mfa_key_str.encode()

    return Config(
        telegram_token=telegram_token,
        admin_ids=admin_ids,
        mikrotik_devices=tuple(mikrotik_devices),
        mfa_enabled=mfa_enabled,
        mfa_session_duration=mfa_session_duration,
        mfa_db_path=mfa_db_path,
        mfa_encryption_key=mfa_encryption_key,
    )


# Singleton config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the singleton config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
