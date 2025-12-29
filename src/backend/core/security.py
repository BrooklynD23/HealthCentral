"""
Security utilities for HealthCentral.

Handles:
- Encryption key management
- DPAPI integration (Windows)
- JWT token generation/validation
- Password hashing
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt
from passlib.context import CryptContext
import base64

from .config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def get_jwt_secret() -> str:
    """Get or generate JWT secret key."""
    if settings.jwt_secret:
        return settings.jwt_secret
    # In production, this should be persisted
    return secrets.token_urlsafe(32)


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


def seal_key_with_dpapi(key: bytes) -> bytes:
    """
    Seal (encrypt) a key using Windows DPAPI.
    
    DPAPI ties the sealed key to the current Windows user account.
    Only that user can unseal it.
    
    Falls back to returning the key unchanged on non-Windows systems.
    """
    if not settings.use_dpapi:
        return key
    
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
        return sealed
    except ImportError:
        # win32crypt not available (non-Windows or missing pywin32)
        return key
    except Exception:
        # DPAPI operation failed
        return key


def unseal_key_with_dpapi(sealed_key: bytes) -> bytes:
    """
    Unseal (decrypt) a key using Windows DPAPI.
    
    Falls back to returning the key unchanged on non-Windows systems.
    """
    if not settings.use_dpapi:
        return sealed_key
    
    try:
        import win32crypt
        # Decrypt using DPAPI
        _, key = win32crypt.CryptUnprotectData(
            sealed_key,
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            0,     # Flags
        )
        return key
    except ImportError:
        return sealed_key
    except Exception:
        return sealed_key
