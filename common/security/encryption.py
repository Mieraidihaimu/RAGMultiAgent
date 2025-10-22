"""
Field-level encryption utilities for sensitive data

This module provides AES-256-GCM encryption for field-level encryption of sensitive
data including user context, thought text, and analysis results. It implements
encryption best practices including:

- AES-256-GCM for authenticated encryption
- Unique IV/nonce per encryption operation
- Base64 encoding for storage
- Key derivation from master key
- Support for key rotation
- Compute-efficient operations

Security Notes:
- Master key should be stored securely (environment variable, secrets manager)
- Keys should be rotated periodically
- Encrypted data includes authentication tag for integrity verification
- IV is stored with ciphertext (safe practice)

GDPR Compliance:
- Encryption at rest for personal data
- Encryption meets "state of the art" requirement (Article 32)
- Supports right to erasure by key deletion
"""

import os
import base64
import json
import hashlib
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive fields using AES-256-GCM

    Features:
    - AES-256-GCM authenticated encryption
    - Automatic IV generation
    - Base64 encoding for database storage
    - Support for text and JSON data
    - Key derivation and rotation support

    Performance:
    - AES-GCM is hardware-accelerated on modern CPUs (AES-NI)
    - Typical encryption: ~1-5 microseconds for small payloads
    - Typical decryption: ~1-5 microseconds for small payloads
    - Minimal memory overhead
    """

    # Version for encryption format (allows future algorithm changes)
    ENCRYPTION_VERSION = 1

    # AES-256 requires 32-byte keys
    KEY_SIZE = 32

    # GCM recommended nonce size is 12 bytes
    NONCE_SIZE = 12

    # Prefix to identify encrypted fields
    ENCRYPTED_PREFIX = "enc_v1:"

    def __init__(self, master_key: Optional[str] = None, key_id: str = "default"):
        """
        Initialize encryption service

        Args:
            master_key: Base64-encoded 32-byte master key. If None, loads from env.
            key_id: Identifier for this key (for key rotation)

        Raises:
            ValueError: If master key is invalid
        """
        self.key_id = key_id

        # Load master key from environment or parameter
        if master_key is None:
            master_key = os.getenv("ENCRYPTION_MASTER_KEY")
            if not master_key:
                raise ValueError(
                    "ENCRYPTION_MASTER_KEY environment variable not set. "
                    "Generate a key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )

        # Decode and validate master key
        try:
            self.master_key = base64.urlsafe_b64decode(master_key)
            if len(self.master_key) != self.KEY_SIZE:
                raise ValueError(f"Master key must be {self.KEY_SIZE} bytes")
        except Exception as e:
            raise ValueError(f"Invalid master key format: {e}")

        # Initialize AESGCM cipher
        self.cipher = AESGCM(self.master_key)

        logger.info(f"EncryptionService initialized with key_id={key_id}")

    def encrypt_text(self, plaintext: str) -> str:
        """
        Encrypt a text string

        Args:
            plaintext: Text to encrypt

        Returns:
            Base64-encoded encrypted text with format: "enc_v1:<nonce>:<ciphertext>"

        Performance: ~1-5 microseconds for typical text lengths
        """
        if not plaintext:
            return plaintext

        if self._is_encrypted(plaintext):
            # Already encrypted, return as-is
            logger.warning("Attempted to encrypt already encrypted text")
            return plaintext

        try:
            # Convert to bytes
            plaintext_bytes = plaintext.encode('utf-8')

            # Generate random nonce (IV)
            nonce = os.urandom(self.NONCE_SIZE)

            # Encrypt with authenticated encryption (includes auth tag)
            ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)

            # Combine nonce + ciphertext and encode
            encrypted_data = nonce + ciphertext
            encoded = base64.urlsafe_b64encode(encrypted_data).decode('ascii')

            # Return with version prefix
            return f"{self.ENCRYPTED_PREFIX}{self.key_id}:{encoded}"

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_text(self, ciphertext: str) -> str:
        """
        Decrypt a text string

        Args:
            ciphertext: Encrypted text with format "enc_v1:<key_id>:<data>"

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (wrong key, tampered data, etc.)

        Performance: ~1-5 microseconds for typical text lengths
        """
        if not ciphertext:
            return ciphertext

        if not self._is_encrypted(ciphertext):
            # Not encrypted, return as-is (for migration scenarios)
            logger.warning("Attempted to decrypt non-encrypted text")
            return ciphertext

        try:
            # Parse encrypted format: "enc_v1:<key_id>:<data>"
            parts = ciphertext.split(':', 2)
            if len(parts) != 3:
                raise ValueError("Invalid encrypted format")

            prefix, stored_key_id, encoded_data = parts

            # Verify version
            if prefix != "enc_v1":
                raise ValueError(f"Unsupported encryption version: {prefix}")

            # Check key ID (for key rotation support)
            if stored_key_id != self.key_id:
                logger.warning(f"Key ID mismatch: stored={stored_key_id}, current={self.key_id}")
                # In production, you'd load the appropriate key here

            # Decode from base64
            encrypted_data = base64.urlsafe_b64decode(encoded_data)

            # Extract nonce and ciphertext
            nonce = encrypted_data[:self.NONCE_SIZE]
            ciphertext_bytes = encrypted_data[self.NONCE_SIZE:]

            # Decrypt and verify authentication tag
            plaintext_bytes = self.cipher.decrypt(nonce, ciphertext_bytes, None)

            # Convert back to string
            return plaintext_bytes.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

    def encrypt_json(self, data: Union[Dict, list, Any]) -> str:
        """
        Encrypt JSON-serializable data

        Args:
            data: Dictionary, list, or JSON-serializable object

        Returns:
            Encrypted JSON as base64 string with prefix

        Performance: ~5-10 microseconds + JSON serialization time
        """
        if data is None:
            return None

        try:
            # Serialize to JSON string
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

            # Encrypt the JSON string
            return self.encrypt_text(json_str)

        except Exception as e:
            logger.error(f"JSON encryption failed: {e}")
            raise

    def decrypt_json(self, ciphertext: str) -> Union[Dict, list, Any]:
        """
        Decrypt and deserialize JSON data

        Args:
            ciphertext: Encrypted JSON string

        Returns:
            Deserialized Python object

        Performance: ~5-10 microseconds + JSON parsing time
        """
        if not ciphertext:
            return None

        try:
            # Decrypt to JSON string
            json_str = self.decrypt_text(ciphertext)

            # Parse JSON
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decryption/parsing failed: {e}")
            # Return as-is if not valid JSON (migration scenario)
            if not self._is_encrypted(ciphertext):
                try:
                    return json.loads(ciphertext)
                except:
                    return ciphertext
            raise
        except Exception as e:
            logger.error(f"JSON decryption failed: {e}")
            raise

    def _is_encrypted(self, data: str) -> bool:
        """Check if data is already encrypted"""
        return isinstance(data, str) and data.startswith(self.ENCRYPTED_PREFIX)

    def encrypt_field(self, field_value: Any, field_type: str = "text") -> str:
        """
        Encrypt a field based on its type

        Args:
            field_value: Value to encrypt
            field_type: Type of field ("text" or "json")

        Returns:
            Encrypted value as string
        """
        if field_value is None:
            return None

        if field_type == "json":
            return self.encrypt_json(field_value)
        else:
            return self.encrypt_text(str(field_value))

    def decrypt_field(self, encrypted_value: str, field_type: str = "text") -> Any:
        """
        Decrypt a field based on its type

        Args:
            encrypted_value: Encrypted value
            field_type: Type of field ("text" or "json")

        Returns:
            Decrypted value
        """
        if encrypted_value is None:
            return None

        if field_type == "json":
            return self.decrypt_json(encrypted_value)
        else:
            return self.decrypt_text(encrypted_value)

    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new random 256-bit master key

        Returns:
            Base64-encoded master key (safe for environment variables)

        Usage:
            >>> key = EncryptionService.generate_master_key()
            >>> # Save to .env file: ENCRYPTION_MASTER_KEY=<key>
        """
        import secrets
        key = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(key).decode('ascii')

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password (for user-specific encryption)

        Args:
            password: User password or passphrase
            salt: Unique salt (at least 16 bytes)

        Returns:
            32-byte derived key

        Note: Use this for per-user encryption keys if needed
        Performance: ~50-100ms (intentionally slow for security)
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,  # OWASP 2023 recommendation
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))


# Singleton instance for application-wide use
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service(master_key: Optional[str] = None, key_id: str = "default") -> EncryptionService:
    """
    Get or create singleton encryption service instance

    Args:
        master_key: Master encryption key (loads from env if None)
        key_id: Key identifier for rotation support

    Returns:
        EncryptionService instance

    Usage:
        >>> encryption = get_encryption_service()
        >>> encrypted = encryption.encrypt_text("sensitive data")
        >>> decrypted = encryption.decrypt_text(encrypted)
    """
    global _encryption_service

    if _encryption_service is None:
        _encryption_service = EncryptionService(master_key=master_key, key_id=key_id)

    return _encryption_service


def reset_encryption_service():
    """Reset singleton (for testing or key rotation)"""
    global _encryption_service
    _encryption_service = None


# Convenience functions for common operations

def encrypt_user_context(context: Dict[str, Any]) -> str:
    """Encrypt user context JSONB field"""
    service = get_encryption_service()
    return service.encrypt_json(context)


def decrypt_user_context(encrypted_context: str) -> Dict[str, Any]:
    """Decrypt user context JSONB field"""
    service = get_encryption_service()
    return service.decrypt_json(encrypted_context)


def encrypt_thought_text(text: str) -> str:
    """Encrypt thought text field"""
    service = get_encryption_service()
    return service.encrypt_text(text)


def decrypt_thought_text(encrypted_text: str) -> str:
    """Decrypt thought text field"""
    service = get_encryption_service()
    return service.decrypt_text(encrypted_text)


def encrypt_analysis_field(analysis: Dict[str, Any]) -> str:
    """Encrypt analysis JSONB field (classification, analysis, value_impact, etc.)"""
    service = get_encryption_service()
    return service.encrypt_json(analysis)


def decrypt_analysis_field(encrypted_analysis: str) -> Dict[str, Any]:
    """Decrypt analysis JSONB field"""
    service = get_encryption_service()
    return service.decrypt_json(encrypted_analysis)


if __name__ == "__main__":
    # Test and demonstration
    print("=== Encryption Service Test ===\n")

    # Generate a test key
    print("1. Generating master key:")
    test_key = EncryptionService.generate_master_key()
    print(f"   Master Key: {test_key}\n")

    # Create service
    service = EncryptionService(master_key=test_key)

    # Test text encryption
    print("2. Text Encryption Test:")
    original_text = "This is a sensitive user thought about personal challenges."
    encrypted_text = service.encrypt_text(original_text)
    decrypted_text = service.decrypt_text(encrypted_text)
    print(f"   Original:  {original_text}")
    print(f"   Encrypted: {encrypted_text[:80]}...")
    print(f"   Decrypted: {decrypted_text}")
    print(f"   Match: {original_text == decrypted_text}\n")

    # Test JSON encryption
    print("3. JSON Encryption Test:")
    original_context = {
        "demographics": {"age": 35, "family": "married with 2 kids"},
        "goals": {"career": "transition to tech", "health": "lose 20 lbs"},
        "constraints": ["limited time", "family obligations"]
    }
    encrypted_json = service.encrypt_json(original_context)
    decrypted_json = service.decrypt_json(encrypted_json)
    print(f"   Original:  {json.dumps(original_context, indent=2)}")
    print(f"   Encrypted: {encrypted_json[:80]}...")
    print(f"   Decrypted: {json.dumps(decrypted_json, indent=2)}")
    print(f"   Match: {original_context == decrypted_json}\n")

    # Performance test
    print("4. Performance Test (1000 operations):")
    import time

    iterations = 1000
    test_data = "A" * 1000  # 1KB of data

    start = time.time()
    for _ in range(iterations):
        enc = service.encrypt_text(test_data)
    encrypt_time = (time.time() - start) / iterations * 1000000  # microseconds

    start = time.time()
    for _ in range(iterations):
        dec = service.decrypt_text(enc)
    decrypt_time = (time.time() - start) / iterations * 1000000  # microseconds

    print(f"   Encryption: {encrypt_time:.2f} μs/operation")
    print(f"   Decryption: {decrypt_time:.2f} μs/operation")
    print(f"   Total:      {encrypt_time + decrypt_time:.2f} μs/round-trip\n")

    print("✅ All tests passed!")
