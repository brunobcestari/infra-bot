#!/usr/bin/env python3
"""
MFA Management CLI Tool

Manage user MFA enrollments for the Telegram infrastructure bot.

Usage:
  python scripts/manage_mfa.py enroll <user_id>     # Enroll user, show QR code
  python scripts/manage_mfa.py list                 # List all enrolled users
  python scripts/manage_mfa.py status <user_id>     # Show user's MFA status
  python scripts/manage_mfa.py reset <user_id>      # Remove user's MFA
  python scripts/manage_mfa.py export-qr <user_id>  # Export QR code to file

Examples:
  # Enroll Telegram user 123456789
  python scripts/manage_mfa.py enroll 123456789

  # List all enrolled users
  python scripts/manage_mfa.py list

  # Check status for user 123456789
  python scripts/manage_mfa.py status 123456789

  # Reset MFA for user 123456789
  python scripts/manage_mfa.py reset 123456789

  # Export QR code as PNG file
  python scripts/manage_mfa.py export-qr 123456789
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from app.mfa.database import MFADatabase
from app.mfa.totp import generate_totp_secret, get_totp_uri
from app.mfa.qr import generate_qr_code, generate_qr_code_ascii
from app.config import load_config


def load_mfa_db() -> MFADatabase:
    """Load MFA database using config settings."""
    config = load_config()

    if not config.mfa_enabled:
        print("❌ Error: MFA is disabled in config.json")
        print("Set mfa.enabled = true to use MFA features")
        sys.exit(1)

    if not config.mfa_encryption_key:
        print("❌ Error: MFA_ENCRYPTION_KEY environment variable not set")
        print("Generate a key: openssl rand -base64 32")
        sys.exit(1)

    return MFADatabase(
        db_path=config.mfa_db_path,
        encryption_key=config.mfa_encryption_key
    )


def cmd_enroll(user_id: int) -> None:
    """Enroll a user in MFA.

    Args:
        user_id: Telegram user ID to enroll
    """
    db = load_mfa_db()

    # Check if already enrolled
    if db.is_user_enrolled(user_id):
        print(f"⚠️  User {user_id} is already enrolled in MFA.")
        response = input("Do you want to re-enroll (reset their secret)? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

        # Disable existing MFA
        db.disable_user_mfa(user_id)
        print(f"✓ Disabled existing MFA for user {user_id}")

    # Generate new TOTP secret
    secret = generate_totp_secret()

    # Generate QR code URI
    uri = get_totp_uri(secret, user_id, issuer="InfraBot")

    # Enroll user
    db.enroll_user(user_id, secret)

    print("\n" + "=" * 70)
    print(f"✅ User {user_id} enrolled in MFA successfully!")
    print("=" * 70)

    # Display QR code as ASCII art
    print("\n📱 Scan this QR code with your authenticator app:\n")
    ascii_qr = generate_qr_code_ascii(uri)
    print(ascii_qr)

    # Optionally display manual secret
    print("\n" + "-" * 70)
    print("🔑 A manual entry secret is available if QR scan doesn't work.")
    show_secret = input("Do you want to display the manual secret now? [y/N]: ")
    if show_secret.lower() == "y":
        print(f"\n    {secret}\n")
    print("-" * 70)

    # Save QR code as PNG
    qr_dir = Path("mfa_qr_codes")
    qr_dir.mkdir(exist_ok=True)
    qr_path = qr_dir / f"{user_id}.png"

    qr_buffer = generate_qr_code(uri)
    with open(qr_path, "wb") as f:
        f.write(qr_buffer.read())

    print(f"\n💾 QR code saved to: {qr_path}")

    print("\n" + "=" * 70)
    print("📋 Next steps:")
    print("=" * 70)
    print("1. User scans the QR code with their authenticator app")
    print("   (Google Authenticator, Authy, 1Password, Bitwarden, etc.)")
    print("2. User can now use MFA-protected commands in Telegram")
    print(f"3. User can check their status with: /mfa_status")
    print("=" * 70 + "\n")


def cmd_list() -> None:
    """List all enrolled users."""
    db = load_mfa_db()
    users = db.list_enrolled_users()

    if not users:
        print("No users enrolled in MFA.")
        return

    print("\n" + "=" * 70)
    print("📋 Enrolled Users")
    print("=" * 70)
    print(f"{'User ID':<15} {'Enrolled':<25} {'Last Used':<20} {'Active'}")
    print("-" * 70)

    for user in users:
        user_id = user['user_id']
        created = user['created_at'].split('.')[0] if user['created_at'] else 'Unknown'
        last_used = user['last_used_at'].split('.')[0] if user['last_used_at'] else 'Never'
        active = '✓' if user['is_active'] else '✗'

        print(f"{user_id:<15} {created:<25} {last_used:<20} {active}")

    print("=" * 70)
    print(f"Total: {len(users)} user(s)\n")


def cmd_status(user_id: int) -> None:
    """Show MFA status for a user.

    Args:
        user_id: Telegram user ID
    """
    db = load_mfa_db()

    if not db.is_user_enrolled(user_id):
        print(f"❌ User {user_id} is not enrolled in MFA.")
        return

    user_info = db.get_user_info(user_id)
    session_id = db.get_user_session(user_id)

    print("\n" + "=" * 70)
    print(f"MFA Status for User {user_id}")
    print("=" * 70)

    print(f"✅ Enrolled:     {user_info['created_at'].split('.')[0]} UTC")
    print(f"🕐 Last used:    {user_info['last_used_at'].split('.')[0] if user_info['last_used_at'] else 'Never'} UTC")
    print(f"🔐 Active:       {'Yes' if user_info['is_active'] else 'No'}")

    if session_id:
        session = db.get_session(session_id)
        if session:
            expires = session['expires_at'].split('.')[0]
            print(f"🟢 Session:      Active (expires {expires} UTC)")
        else:
            print(f"🔴 Session:      No active session")
    else:
        print(f"🔴 Session:      No active session")

    print("=" * 70 + "\n")


def cmd_reset(user_id: int) -> None:
    """Reset MFA for a user.

    Args:
        user_id: Telegram user ID
    """
    db = load_mfa_db()

    if not db.is_user_enrolled(user_id):
        print(f"❌ User {user_id} is not enrolled in MFA.")
        return

    print(f"\n⚠️  WARNING: This will remove MFA for user {user_id}")
    print("They will need to re-enroll to use MFA-protected commands.")
    response = input("\nAre you sure? [y/N]: ")

    if response.lower() != 'y':
        print("Cancelled.")
        return

    db.disable_user_mfa(user_id)
    print(f"\n✅ MFA reset for user {user_id}")
    print("User will need to re-enroll to use MFA again.\n")


def cmd_export_qr(user_id: int) -> None:
    """Export QR code for an enrolled user.

    Args:
        user_id: Telegram user ID
    """
    db = load_mfa_db()

    if not db.is_user_enrolled(user_id):
        print(f"❌ User {user_id} is not enrolled in MFA.")
        return

    # Get user's secret (decrypt it)
    secret = db.get_user_secret(user_id)
    if not secret:
        print(f"❌ Could not retrieve secret for user {user_id}")
        return

    # Generate QR code URI
    uri = get_totp_uri(secret, user_id, issuer="InfraBot")

    # Display ASCII QR
    print("\n📱 QR Code for User {user_id}:\n")
    ascii_qr = generate_qr_code_ascii(uri)
    print(ascii_qr)

    # Save as PNG
    qr_dir = Path("mfa_qr_codes")
    qr_dir.mkdir(exist_ok=True)
    qr_path = qr_dir / f"{user_id}.png"

    qr_buffer = generate_qr_code(uri)
    with open(qr_path, "wb") as f:
        f.write(qr_buffer.read())

    print(f"\n💾 QR code saved to: {qr_path}")


def print_usage() -> None:
    """Print usage information."""
    print(__doc__)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "enroll":
            if len(sys.argv) < 3:
                print("❌ Error: Missing user_id argument")
                print("Usage: python scripts/manage_mfa.py enroll <user_id>")
                sys.exit(1)
            try:
                user_id = int(sys.argv[2])
            except ValueError:
                print("❌ Error: user_id must be a number")
                sys.exit(1)
            cmd_enroll(user_id)

        elif command == "list":
            cmd_list()

        elif command == "status":
            if len(sys.argv) < 3:
                print("❌ Error: Missing user_id argument")
                print("Usage: python scripts/manage_mfa.py status <user_id>")
                sys.exit(1)
            try:
                user_id = int(sys.argv[2])
            except ValueError:
                print("❌ Error: user_id must be a number")
                sys.exit(1)
            cmd_status(user_id)

        elif command == "reset":
            if len(sys.argv) < 3:
                print("❌ Error: Missing user_id argument")
                print("Usage: python scripts/manage_mfa.py reset <user_id>")
                sys.exit(1)
            try:
                user_id = int(sys.argv[2])
            except ValueError:
                print("❌ Error: user_id must be a number")
                sys.exit(1)
            cmd_reset(user_id)

        elif command == "export-qr":
            if len(sys.argv) < 3:
                print("❌ Error: Missing user_id argument")
                print("Usage: python scripts/manage_mfa.py export-qr <user_id>")
                sys.exit(1)
            try:
                user_id = int(sys.argv[2])
            except ValueError:
                print("❌ Error: user_id must be a number")
                sys.exit(1)
            cmd_export_qr(user_id)

        else:
            print(f"❌ Error: Unknown command '{command}'")
            print_usage()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
