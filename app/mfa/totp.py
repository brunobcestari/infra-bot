"""TOTP (Time-based One-Time Password) utilities using PyOTP."""

import secrets
import pyotp


def generate_totp_secret() -> str:
    """Generate a new base32 TOTP secret.

    Returns:
        Base32-encoded random secret suitable for TOTP
    """
    return pyotp.random_base32()


def get_totp_uri(secret: str, user_id: int, issuer: str = "InfraBot") -> str:
    """Generate TOTP provisioning URI for QR code.

    Args:
        secret: Base32 TOTP secret
        user_id: Telegram user ID (used as account name)
        issuer: Service name displayed in authenticator app

    Returns:
        otpauth:// URI for QR code generation
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=str(user_id),
        issuer_name=issuer
    )


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify TOTP code with time window tolerance.

    Args:
        secret: Base32 TOTP secret
        code: 6-digit code from user
        valid_window: Number of 30-second windows before/after to accept (default 1 = ±30s)

    Returns:
        True if code is valid within the time window
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)


def get_current_totp(secret: str) -> str:
    """Get current TOTP code.

    Useful for testing/debugging.

    Args:
        secret: Base32 TOTP secret

    Returns:
        Current 6-digit TOTP code
    """
    totp = pyotp.TOTP(secret)
    return totp.now()


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate single-use backup codes.

    Args:
        count: Number of backup codes to generate

    Returns:
        List of backup codes in format XXXX-XXXX
    """
    return [
        f"{secrets.randbelow(10000):04d}-{secrets.randbelow(10000):04d}"
        for _ in range(count)
    ]
