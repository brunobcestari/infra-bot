"""Encryption utilities for MFA secrets."""

import base64
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionHelper:
    """Encrypt/decrypt TOTP secrets using Fernet (AES-128)."""

    def __init__(self, encryption_key: bytes):
        """Initialize encryption helper with master key.

        Args:
            encryption_key: Master encryption key from environment variable
        """
        # Derive Fernet key from master key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'infra-bot-mfa-salt-2026',  # Fixed salt for key derivation
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(encryption_key))
        self.fernet = Fernet(derived_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return base64 string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        encrypted = self.fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt from base64 string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        decrypted = self.fernet.decrypt(ciphertext.encode())
        return decrypted.decode()

    @staticmethod
    def hash_backup_code(code: str) -> str:
        """Hash backup code with bcrypt (one-way).

        Args:
            code: Backup code to hash

        Returns:
            Bcrypt hash string
        """
        return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_backup_code(code: str, hashed: str) -> bool:
        """Verify backup code against hash.

        Args:
            code: Backup code to verify
            hashed: Bcrypt hash to compare against

        Returns:
            True if code matches hash
        """
        return bcrypt.checkpw(code.encode(), hashed.encode())
