"""
Document Chunking Module for RAG Pipeline.

Splits documents into overlapping chunks for embedding and retrieval.
Preserves sentence boundaries and tracks provenance.
"""

import re
import uuid
from typing import Optional
from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Configuration for chunking behavior."""
    chunk_size: int = 200  # Target size in tokens (approximate)
    chunk_overlap: int = 50  # Overlap between chunks
    min_chunk_size: int = 20  # Minimum chunk size to keep
    chars_per_token: float = 4.0  # Approximate chars per token


class ChunkingModule:
    """
    Document chunking for RAG retrieval.

    Splits text into semantically coherent chunks that:
    - Respect sentence boundaries when possible
    - Include overlap for context continuity
    - Track provenance (page, character positions)
    """

    def __init__(
        self,
        chunk_size: int = 200,
        chunk_overlap: int = 50,
        min_chunk_size: int = 20,
    ):
        """
        Initialize chunking module.

        Args:
            chunk_size: Target chunk size in tokens (approximate)
            chunk_overlap: Number of tokens to overlap between chunks
            min_chunk_size: Minimum tokens to keep a chunk
        """
        self.config = ChunkConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
        )
        self._chars_per_token = 4.0

    def chunk_document(
        self,
        doc_id: str,
        text: str,
        page_number: int = 1,
        chunk_type: str = "text",
    ) -> list[dict]:
        """
        Chunk document text into overlapping segments.

        Args:
            doc_id: Document ID for provenance
            text: Full document text
            page_number: Page number (for multi-page docs)
            chunk_type: Type of chunk (text, table, header)

        Returns:
            List of chunk dictionaries with provenance
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace
        text = self._normalize_text(text)

        if not text:
            return []

        # Split into sentences first
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        # Build chunks from sentences
        chunks = self._build_chunks_from_sentences(sentences, text)

        # Add metadata to each chunk
        result = []
        for i, (chunk_text, start_char, end_char) in enumerate(chunks):
            # Skip chunks that are too small
            token_count = self._estimate_tokens(chunk_text)
            if token_count < self.config.min_chunk_size:
                continue

            result.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "text": chunk_text,
                "page_number": page_number,
                "chunk_index": i,
                "start_char": start_char,
                "end_char": end_char,
                "token_count": token_count,
                "chunk_type": chunk_type,
            })

        # If no valid chunks, create one from full text if it's meaningful
        if not result and len(text.strip()) > 0:
            result.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "text": text.strip(),
                "page_number": page_number,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": len(text),
                "token_count": self._estimate_tokens(text),
                "chunk_type": chunk_type,
            })

        return result

    def _normalize_text(self, text: str) -> str:
        """Normalize whitespace and clean text."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """
        Split text into sentences with positions.

        Returns list of (sentence_text, start_pos, end_pos)
        """
        sentences = []

        # Pattern for sentence endings
        # Matches: . ! ? followed by space and capital, or end of string
        sentence_pattern = r'([.!?:])(?=\s+[A-Z]|\s*$)'

        current_pos = 0
        text_remaining = text

        # Find sentence boundaries
        while text_remaining:
            match = re.search(sentence_pattern, text_remaining)

            if match:
                # End of sentence found
                end_rel = match.end()
                sentence = text_remaining[:end_rel].strip()
                if sentence:
                    sentences.append((
                        sentence,
                        current_pos,
                        current_pos + len(text_remaining[:end_rel].rstrip())
                    ))
                current_pos += end_rel
                text_remaining = text_remaining[end_rel:].lstrip()
            else:
                # No more sentence endings, take the rest
                if text_remaining.strip():
                    sentences.append((
                        text_remaining.strip(),
                        current_pos,
                        current_pos + len(text_remaining.rstrip())
                    ))
                break

        return sentences

    def _build_chunks_from_sentences(
        self,
        sentences: list[tuple[str, int, int]],
        full_text: str,
    ) -> list[tuple[str, int, int]]:
        """
        Build chunks from sentences, respecting size limits and overlap.

        Returns list of (chunk_text, start_char, end_char)
        """
        if not sentences:
            return []

        target_chars = int(self.config.chunk_size * self._chars_per_token)
        overlap_chars = int(self.config.chunk_overlap * self._chars_per_token)

        chunks = []
        current_chunk_sentences = []
        current_chunk_start = sentences[0][1]
        current_length = 0

        for sentence, start, end in sentences:
            sentence_length = len(sentence)

            # Check if adding this sentence exceeds target
            if current_length + sentence_length > target_chars and current_chunk_sentences:
                # Emit current chunk
                chunk_text = " ".join(s[0] for s in current_chunk_sentences)
                chunk_end = current_chunk_sentences[-1][2]
                chunks.append((chunk_text, current_chunk_start, chunk_end))

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences, overlap_chars
                )
                current_chunk_sentences = overlap_sentences
                if overlap_sentences:
                    current_chunk_start = overlap_sentences[0][1]
                    current_length = sum(len(s[0]) for s in overlap_sentences)
                else:
                    current_chunk_start = start
                    current_length = 0

            # Add sentence to current chunk
            current_chunk_sentences.append((sentence, start, end))
            current_length += sentence_length

        # Emit final chunk
        if current_chunk_sentences:
            chunk_text = " ".join(s[0] for s in current_chunk_sentences)
            chunk_end = current_chunk_sentences[-1][2]
            chunks.append((chunk_text, current_chunk_start, chunk_end))

        return chunks

    def _get_overlap_sentences(
        self,
        sentences: list[tuple[str, int, int]],
        overlap_chars: int,
    ) -> list[tuple[str, int, int]]:
        """
        Get sentences for overlap from end of chunk.

        Takes sentences from the end that fit in overlap_chars.
        """
        result = []
        total_chars = 0

        for sentence in reversed(sentences):
            if total_chars + len(sentence[0]) <= overlap_chars:
                result.insert(0, sentence)
                total_chars += len(sentence[0])
            else:
                break

        return result

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from character count."""
        return max(1, int(len(text) / self._chars_per_token))

    def chunk_pdf_pages(
        self,
        doc_id: str,
        pages: list[str],
    ) -> list[dict]:
        """
        Chunk a multi-page PDF document.

        Args:
            doc_id: Document ID
            pages: List of page texts

        Returns:
            List of chunks across all pages
        """
        all_chunks = []
        global_index = 0

        for page_num, page_text in enumerate(pages, start=1):
            page_chunks = self.chunk_document(
                doc_id=doc_id,
                text=page_text,
                page_number=page_num,
            )

            # Update chunk indices to be global
            for chunk in page_chunks:
                chunk["chunk_index"] = global_index
                global_index += 1

            all_chunks.extend(page_chunks)

        return all_chunks
