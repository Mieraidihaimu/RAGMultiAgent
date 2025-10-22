"""
Security utilities for the AI Thought Processor

This module provides security utilities including:
- Field-level encryption for sensitive data
- Key management and rotation
- Encryption/decryption helpers

Usage:
    from common.security import get_encryption_service, encrypt_user_context

    # Get encryption service
    encryption = get_encryption_service()

    # Encrypt data
    encrypted_context = encrypt_user_context({"goal": "sensitive info"})
    encrypted_text = encryption.encrypt_text("private thought")

    # Decrypt data
    context = decrypt_user_context(encrypted_context)
    text = encryption.decrypt_text(encrypted_text)
"""

from .encryption import (
    EncryptionService,
    get_encryption_service,
    reset_encryption_service,
    encrypt_user_context,
    decrypt_user_context,
    encrypt_thought_text,
    decrypt_thought_text,
    encrypt_analysis_field,
    decrypt_analysis_field,
)

__all__ = [
    "EncryptionService",
    "get_encryption_service",
    "reset_encryption_service",
    "encrypt_user_context",
    "decrypt_user_context",
    "encrypt_thought_text",
    "decrypt_thought_text",
    "encrypt_analysis_field",
    "decrypt_analysis_field",
]
