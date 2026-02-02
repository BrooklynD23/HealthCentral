"""
Document decryption helper for encrypted document access.

Provides a service layer for decrypting stored documents for read operations
like PDF text extraction and page rendering.
"""

import io
import logging
from pathlib import Path
from typing import Optional

from .config import settings
from .profile_database import get_profile_db_manager

logger = logging.getLogger(__name__)


def get_profile_encryption_key(profile_id: str) -> Optional[bytes]:
    """
    Get the encryption key for a profile from its active database connection.

    The encryption key is only available when the profile has an active
    session (i.e., is logged in). This ensures PHI is only accessible
    to authenticated users.

    Args:
        profile_id: The profile UUID

    Returns:
        The 32-byte encryption key if the profile is connected, None otherwise
    """
    db_manager = get_profile_db_manager()
    connection = db_manager.get_connection(profile_id)
    if connection:
        return connection._encryption_key
    return None


def get_decrypted_document(
    profile_id: str,
    document_id: str,
    vault_path: Optional[Path] = None,
) -> io.BytesIO:
    """
    Decrypt a stored document and return as BytesIO for processing.

    This function retrieves the encryption key from the active profile session,
    decrypts the stored document, and returns it as a BytesIO object suitable
    for use with libraries like pdfplumber that expect file-like objects.

    Args:
        profile_id: The profile UUID
        document_id: The document UUID
        vault_path: Optional override for vault path (defaults to settings)

    Returns:
        BytesIO containing the decrypted document data

    Raises:
        PermissionError: If the profile is not connected (no encryption key available)
        FileNotFoundError: If the document file doesn't exist
        ValueError: If decryption fails
    """
    from modules.ingest import IngestModule

    # Get encryption key from active session
    encryption_key = get_profile_encryption_key(profile_id)
    if encryption_key is None:
        raise PermissionError(
            f"Profile {profile_id} is not connected. Cannot decrypt documents."
        )

    # Determine vault path
    if vault_path is None:
        vault_path = Path(settings.app_data_path) / "vaults" / profile_id

    # Create IngestModule with encryption key to decrypt
    ingest = IngestModule(vault_path, encryption_key=encryption_key)

    # Decrypt the document
    try:
        decrypted_bytes = ingest.decrypt_document(document_id)
    except FileNotFoundError:
        raise FileNotFoundError(f"Document {document_id} not found in vault")
    except Exception as e:
        raise ValueError(f"Failed to decrypt document {document_id}: {e}") from e

    return io.BytesIO(decrypted_bytes)
