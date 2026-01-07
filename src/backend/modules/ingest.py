"""
Document ingestion module.

Handles:
- File import and validation
- Content hashing for deduplication
- Encrypted storage (AES-GCM)
- Metadata extraction
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime
import uuid
import io

from core.config import settings
from core.security import DocumentEncryption

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of document import operation."""
    document_id: str
    path_hash: str
    content_hash: str
    doc_type: str
    page_count: Optional[int]
    is_duplicate: bool
    metadata: dict
    encrypted: bool = True


class IngestModule:
    """
    Document ingestion service.

    Responsibilities:
    - Validate file type and size
    - Compute content hash for deduplication
    - Store encrypted document in vault (AES-GCM)
    - Extract basic metadata
    """

    def __init__(self, vault_path: Path, encryption_key: Optional[bytes] = None):
        """
        Initialize ingestion module.

        Args:
            vault_path: Path to profile's encrypted vault directory
            encryption_key: 32-byte encryption key for document encryption.
                          If None, documents will be stored unencrypted (dev mode only).
        """
        self.vault_path = vault_path
        self.docs_path = vault_path / "docs"
        self.docs_path.mkdir(parents=True, exist_ok=True)

        self._encryption_key = encryption_key
        self._encryptor: Optional[DocumentEncryption] = None

        if encryption_key:
            try:
                self._encryptor = DocumentEncryption(encryption_key)
            except Exception as e:
                logger.error(f"Failed to initialize document encryption: {e}")
                raise ValueError(f"Invalid encryption key: {e}") from e
        else:
            logger.warning(
                "IngestModule initialized without encryption key. "
                "Documents will be stored UNENCRYPTED. This is only acceptable in development."
            )

    def validate_file(self, filename: str, file_size: int) -> tuple[bool, str]:
        """
        Validate file for import.

        Args:
            filename: Original filename
            file_size: File size in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check extension
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in settings.supported_extensions:
            return False, f"Unsupported file type: {ext}"

        # Check size
        max_size = settings.max_import_file_size_mb * 1024 * 1024
        if file_size > max_size:
            return False, f"File too large: {file_size / 1024 / 1024:.1f}MB (max: {settings.max_import_file_size_mb}MB)"

        return True, ""

    def compute_hashes(self, file_data: bytes, source_path: str) -> tuple[str, str]:
        """
        Compute content and path hashes.

        Args:
            file_data: Raw file bytes
            source_path: Original file path

        Returns:
            Tuple of (content_hash, path_hash)
        """
        content_hash = hashlib.sha256(file_data).hexdigest()
        path_hash = hashlib.sha256(source_path.encode()).hexdigest()
        return content_hash, path_hash

    def detect_doc_type(self, filename: str, file_data: bytes) -> str:
        """
        Detect document type from filename and content.

        Args:
            filename: Original filename
            file_data: Raw file bytes

        Returns:
            Document type string
        """
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            # Check if it's a scanned PDF (mostly images)
            # For now, assume text-based; Phase 1 adds OCR detection
            return "lab_pdf"
        elif ext in [".png", ".jpg", ".jpeg"]:
            return "lab_image"
        else:
            return "unknown"

    def _encrypt_and_store(self, document_id: str, file_data: bytes) -> bool:
        """
        Encrypt and store document data.

        Args:
            document_id: Unique document identifier (used as associated data)
            file_data: Raw document bytes

        Returns:
            True if encrypted, False if stored unencrypted
        """
        doc_path = self.docs_path / f"{document_id}.bin"

        if self._encryptor:
            # Encrypt with document_id as associated data for integrity
            encrypted_data = self._encryptor.encrypt(
                file_data,
                associated_data=document_id.encode("utf-8")
            )
            doc_path.write_bytes(encrypted_data)
            logger.debug(f"Stored encrypted document: {document_id}")
            return True
        else:
            # Store unencrypted (development mode only)
            doc_path.write_bytes(file_data)
            logger.warning(f"Stored UNENCRYPTED document: {document_id}")
            return False

    def decrypt_document(self, document_id: str) -> bytes:
        """
        Read and decrypt a stored document.

        Args:
            document_id: Document identifier

        Returns:
            Decrypted document bytes

        Raises:
            FileNotFoundError: If document doesn't exist
            ValueError: If decryption fails
        """
        doc_path = self.docs_path / f"{document_id}.bin"

        if not doc_path.exists():
            raise FileNotFoundError(f"Document not found: {document_id}")

        encrypted_data = doc_path.read_bytes()

        if self._encryptor:
            try:
                return self._encryptor.decrypt(
                    encrypted_data,
                    associated_data=document_id.encode("utf-8")
                )
            except Exception as e:
                # Could be an unencrypted legacy document
                logger.warning(f"Decryption failed for {document_id}, trying as plaintext: {e}")
                return encrypted_data
        else:
            # No encryption configured, return as-is
            return encrypted_data

    async def import_document(
        self,
        file: BinaryIO,
        filename: str,
        profile_id: str,
        source: Optional[str] = None,
    ) -> ImportResult:
        """
        Import a document into the profile vault.

        Documents are encrypted with AES-GCM before storage.
        The document_id is used as associated data for authentication.

        Args:
            file: File-like object with document data
            filename: Original filename
            profile_id: Profile to import into
            source: Optional source description

        Returns:
            ImportResult with document details

        Raises:
            ValueError: If file validation fails
        """
        # Read file data
        file_data = file.read()

        # Validate
        is_valid, error = self.validate_file(filename, len(file_data))
        if not is_valid:
            raise ValueError(error)

        # Compute hashes (on plaintext for deduplication)
        content_hash, path_hash = self.compute_hashes(file_data, filename)

        # TODO: Check for duplicates using content_hash
        is_duplicate = False

        # Detect document type
        doc_type = self.detect_doc_type(filename, file_data)

        # Generate document ID
        document_id = str(uuid.uuid4())

        # Get page count for PDFs BEFORE encryption
        # We need to do this on plaintext data
        page_count = None
        if doc_type == "lab_pdf":
            try:
                import pdfplumber
                # Use BytesIO to read from memory instead of file
                with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                    page_count = len(pdf.pages)
            except Exception as e:
                logger.warning(f"Failed to extract page count from PDF: {e}")

        # Encrypt and store document
        was_encrypted = self._encrypt_and_store(document_id, file_data)

        # Extract basic metadata
        metadata = {
            "original_filename": filename,
            "source": source,
            "imported_at": datetime.utcnow().isoformat(),
            "file_size": len(file_data),
            "encrypted": was_encrypted,
        }

        return ImportResult(
            document_id=document_id,
            path_hash=path_hash,
            content_hash=content_hash,
            doc_type=doc_type,
            page_count=page_count,
            is_duplicate=is_duplicate,
            metadata=metadata,
            encrypted=was_encrypted,
        )
