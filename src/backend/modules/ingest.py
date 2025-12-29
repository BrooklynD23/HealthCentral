"""
Document ingestion module.

Handles:
- File import and validation
- Content hashing for deduplication
- Encrypted storage
- Metadata extraction
"""

import hashlib
from pathlib import Path
from typing import Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime
import uuid

from core.config import settings


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


class IngestModule:
    """
    Document ingestion service.
    
    Responsibilities:
    - Validate file type and size
    - Compute content hash for deduplication
    - Store encrypted document in vault
    - Extract basic metadata
    """
    
    def __init__(self, vault_path: Path):
        """
        Initialize ingestion module.
        
        Args:
            vault_path: Path to profile's encrypted vault directory
        """
        self.vault_path = vault_path
        self.docs_path = vault_path / "docs"
        self.docs_path.mkdir(parents=True, exist_ok=True)
    
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
    
    async def import_document(
        self,
        file: BinaryIO,
        filename: str,
        profile_id: str,
        source: Optional[str] = None,
    ) -> ImportResult:
        """
        Import a document into the profile vault.
        
        Args:
            file: File-like object with document data
            filename: Original filename
            profile_id: Profile to import into
            source: Optional source description
            
        Returns:
            ImportResult with document details
        """
        # Read file data
        file_data = file.read()
        
        # Validate
        is_valid, error = self.validate_file(filename, len(file_data))
        if not is_valid:
            raise ValueError(error)
        
        # Compute hashes
        content_hash, path_hash = self.compute_hashes(file_data, filename)
        
        # TODO: Check for duplicates using content_hash
        is_duplicate = False
        
        # Detect document type
        doc_type = self.detect_doc_type(filename, file_data)
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # TODO: Encrypt and store document
        # For now, store plaintext (encryption to be added)
        doc_path = self.docs_path / f"{document_id}.bin"
        doc_path.write_bytes(file_data)
        
        # Extract basic metadata
        metadata = {
            "original_filename": filename,
            "source": source,
            "imported_at": datetime.utcnow().isoformat(),
            "file_size": len(file_data),
        }
        
        # Get page count for PDFs
        page_count = None
        if doc_type == "lab_pdf":
            try:
                import pdfplumber
                with pdfplumber.open(doc_path) as pdf:
                    page_count = len(pdf.pages)
            except Exception:
                pass
        
        return ImportResult(
            document_id=document_id,
            path_hash=path_hash,
            content_hash=content_hash,
            doc_type=doc_type,
            page_count=page_count,
            is_duplicate=is_duplicate,
            metadata=metadata,
        )
