"""
Security utilities for HealthCentral.

Handles:
- Encryption key management
- DPAPI integration (Windows)
- JWT token generation/validation
- Password hashing
- AES-GCM document encryption
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext
import base64

from .config import settings

logger = logging.getLogger(__name__)


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Module-level JWT secret cache
_jwt_secret_cache: Optional[str] = None


class KeySealingError(Exception):
    """Raised when key sealing/unsealing fails and cannot be recovered."""
    pass


def _get_jwt_secret_path() -> Path:
    """Get the path to the persisted JWT secret file."""
    return Path(settings.app_data_path) / ".jwt_secret"


def get_jwt_secret() -> str:
    """
    Get or generate and persist JWT secret key.

    The secret is persisted to ensure sessions survive server restarts.
    """
    global _jwt_secret_cache

    # Return cached value if available
    if _jwt_secret_cache:
        return _jwt_secret_cache

    # Check settings first
    if settings.jwt_secret:
        _jwt_secret_cache = settings.jwt_secret
        return _jwt_secret_cache

    # Try to load from persisted file
    secret_path = _get_jwt_secret_path()
    try:
        if secret_path.exists():
            _jwt_secret_cache = secret_path.read_text().strip()
            return _jwt_secret_cache
    except Exception as e:
        logger.warning(f"Failed to read JWT secret from {secret_path}: {e}")

    # Generate new secret and persist it
    _jwt_secret_cache = secrets.token_urlsafe(32)
    try:
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        # Write with restrictive permissions
        secret_path.write_text(_jwt_secret_cache)
        # Try to set file permissions (Unix-like systems)
        try:
            secret_path.chmod(0o600)
        except (OSError, AttributeError):
            pass  # Windows doesn't support chmod the same way
        logger.info(f"Generated and persisted new JWT secret to {secret_path}")
    except Exception as e:
        logger.warning(f"Failed to persist JWT secret: {e}. Sessions will not survive restart.")

    return _jwt_secret_cache


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_encryption_key() -> bytes:
    """Generate a new 256-bit encryption key."""
    return Fernet.generate_key()


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive an encryption key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # OWASP recommended minimum
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def generate_salt() -> bytes:
    """Generate a cryptographically secure salt."""
    return os.urandom(16)


class EncryptionManager:
    """
    Manages encryption/decryption of sensitive data.
    
    In local mode, uses Windows DPAPI when available.
    Falls back to Fernet symmetric encryption.
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption manager.
        
        Args:
            key: Encryption key. If None, a new key is generated.
        """
        self._key = key or generate_encryption_key()
        self._fernet = Fernet(self._key)
    
    @property
    def key(self) -> bytes:
        """Get the encryption key (for secure storage)."""
        return self._key
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data."""
        return self._fernet.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data."""
        return self._fernet.decrypt(encrypted_data)
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt a string and return base64-encoded result."""
        encrypted = self.encrypt(text.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("ascii")
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a base64-encoded encrypted string."""
        encrypted = base64.urlsafe_b64decode(encrypted_text.encode("ascii"))
        return self.decrypt(encrypted).decode("utf-8")


def is_dpapi_available() -> bool:
    """Check if Windows DPAPI is available on this system."""
    try:
        import win32crypt
        return True
    except ImportError:
        return False


def seal_key_with_dpapi(key: bytes, fallback_password: Optional[str] = None) -> tuple[bytes, str]:
    """
    Seal (encrypt) a key using Windows DPAPI or password-based encryption.

    DPAPI ties the sealed key to the current Windows user account.
    On non-Windows systems or if DPAPI fails, uses password-based encryption.

    Args:
        key: The encryption key to seal
        fallback_password: Password to use if DPAPI is unavailable

    Returns:
        Tuple of (sealed_key, seal_method) where seal_method is 'dpapi' or 'password'

    Raises:
        KeySealingError: If sealing fails and no fallback is available
    """
    if settings.use_dpapi and is_dpapi_available():
        try:
            import win32crypt
            # Encrypt using DPAPI with user scope
            sealed = win32crypt.CryptProtectData(
                key,
                "HealthCentral Profile Key",
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0,     # Flags
            )
            return sealed, "dpapi"
        except Exception as e:
            logger.warning(f"DPAPI sealing failed: {e}")
            # Fall through to password-based encryption

    # Use password-based encryption as fallback
    if fallback_password:
        salt = generate_salt()
        derived_key = derive_key_from_password(fallback_password, salt)
        fernet = Fernet(derived_key)
        encrypted = fernet.encrypt(key)
        # Prepend salt to encrypted data
        sealed = salt + encrypted
        return sealed, "password"

    # No DPAPI and no password - fail securely
    raise KeySealingError(
        "Cannot seal key: DPAPI is unavailable and no fallback password provided. "
        "On non-Windows systems, profile password is required."
    )


def unseal_key_with_dpapi(
    sealed_key: bytes,
    seal_method: str,
    fallback_password: Optional[str] = None
) -> bytes:
    """
    Unseal (decrypt) a key using Windows DPAPI or password-based decryption.

    Args:
        sealed_key: The sealed key to decrypt
        seal_method: How the key was sealed ('dpapi' or 'password')
        fallback_password: Password if seal_method is 'password'

    Returns:
        The unsealed encryption key

    Raises:
        KeySealingError: If unsealing fails
    """
    if seal_method == "dpapi":
        if not is_dpapi_available():
            raise KeySealingError(
                "Cannot unseal key: Key was sealed with DPAPI but DPAPI is not available. "
                "This key can only be unsealed on Windows by the original user."
            )
        try:
            import win32crypt
            _, key = win32crypt.CryptUnprotectData(
                sealed_key,
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0,     # Flags
            )
            return key
        except Exception as e:
            raise KeySealingError(f"DPAPI unsealing failed: {e}") from e

    elif seal_method == "password":
        if not fallback_password:
            raise KeySealingError(
                "Cannot unseal key: Key was sealed with password but no password provided."
            )
        # Extract salt (first 16 bytes) and encrypted data
        if len(sealed_key) < 17:
            raise KeySealingError("Invalid sealed key format")
        salt = sealed_key[:16]
        encrypted = sealed_key[16:]
        try:
            derived_key = derive_key_from_password(fallback_password, salt)
            fernet = Fernet(derived_key)
            return fernet.decrypt(encrypted)
        except Exception as e:
            raise KeySealingError(f"Password-based unsealing failed: {e}") from e

    else:
        raise KeySealingError(f"Unknown seal method: {seal_method}")


# Legacy functions for backward compatibility during migration
def seal_key_with_dpapi_legacy(key: bytes) -> bytes:
    """
    DEPRECATED: Legacy seal function that returns unprotected key on failure.

    WARNING: This function is insecure and only exists for migration purposes.
    Use seal_key_with_dpapi() instead.
    """
    logger.warning("Using legacy insecure key sealing - migrate to seal_key_with_dpapi()")
    if not settings.use_dpapi:
        return key

    try:
        import win32crypt
        sealed = win32crypt.CryptProtectData(
            key,
            "HealthCentral Profile Key",
            None, None, None, 0,
        )
        return sealed
    except Exception:
        return key


def unseal_key_with_dpapi_legacy(sealed_key: bytes) -> bytes:
    """
    DEPRECATED: Legacy unseal function that returns key unchanged on failure.

    WARNING: This function is insecure and only exists for migration purposes.
    Use unseal_key_with_dpapi() instead.
    """
    logger.warning("Using legacy insecure key unsealing - migrate to unseal_key_with_dpapi()")
    if not settings.use_dpapi:
        return sealed_key

    try:
        import win32crypt
        _, key = win32crypt.CryptUnprotectData(
            sealed_key, None, None, None, 0,
        )
        return key
    except Exception:
        return sealed_key


class DocumentEncryption:
    """
    AES-GCM encryption for document storage.

    Provides authenticated encryption with per-document IVs.
    """

    # IV/nonce size for AES-GCM (96 bits recommended by NIST)
    IV_SIZE = 12

    def __init__(self, key: bytes):
        """
        Initialize document encryption.

        Args:
            key: 256-bit (32 byte) encryption key
        """
        if len(key) != 32:
            # Key might be base64-encoded Fernet key
            if len(key) == 44:  # Base64-encoded 32 bytes
                key = base64.urlsafe_b64decode(key)
            else:
                raise ValueError(f"Key must be 32 bytes, got {len(key)}")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Encrypt data with AES-GCM.

        Args:
            plaintext: Data to encrypt
            associated_data: Optional additional authenticated data (e.g., document_id)

        Returns:
            IV + ciphertext (IV prepended for storage)
        """
        iv = os.urandom(self.IV_SIZE)
        ciphertext = self._aesgcm.encrypt(iv, plaintext, associated_data)
        return iv + ciphertext

    def decrypt(self, ciphertext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt data with AES-GCM.

        Args:
            ciphertext: IV + encrypted data
            associated_data: Must match what was used during encryption

        Returns:
            Decrypted plaintext

        Raises:
            cryptography.exceptions.InvalidTag: If authentication fails
        """
        if len(ciphertext) < self.IV_SIZE + 16:  # IV + minimum tag size
            raise ValueError("Ciphertext too short")
        iv = ciphertext[:self.IV_SIZE]
        actual_ciphertext = ciphertext[self.IV_SIZE:]
        return self._aesgcm.decrypt(iv, actual_ciphertext, associated_data)
