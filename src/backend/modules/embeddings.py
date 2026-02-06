"""
Embeddings Module for RAG Pipeline.

Generates vector embeddings for text chunks using local models.
Supports caching and batch processing for efficiency.
"""

import math
import re
import struct
from dataclasses import dataclass
import hashlib


@dataclass
class EmbeddingsConfig:
    """Configuration for embeddings generation."""
    model_name: str = "all-MiniLM-L6-v2"
    dimensions: int = 384
    batch_size: int = 32
    normalize: bool = True


class EmbeddingsModule:
    """
    Text embedding generation for RAG retrieval.

    Uses sentence-transformers for local, privacy-preserving embeddings.
    Falls back to simple hash-based embeddings if model unavailable.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        use_fallback: bool = True,
    ):
        """
        Initialize embeddings module.

        Args:
            model_name: Name of sentence-transformers model
            use_fallback: Use hash-based fallback if model unavailable
        """
        self.config = EmbeddingsConfig(model_name=model_name)
        self.use_fallback = use_fallback
        self._model = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of embedding model."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.config.model_name)
            self.config.dimensions = self._model.get_sentence_embedding_dimension()
        except ImportError:
            if not self.use_fallback:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            # Use fallback mode
            self._model = None
        except Exception as e:
            if not self.use_fallback:
                raise
            self._model = None

        self._initialized = True

    def embed_chunks(
        self,
        chunks: list[dict],
    ) -> list[dict]:
        """
        Generate embeddings for a list of chunks.

        Args:
            chunks: List of chunk dicts with 'text' and 'chunk_id' fields

        Returns:
            List of embedding dicts with vector and metadata
        """
        if not chunks:
            return []

        self._ensure_initialized()

        # Extract texts
        texts = [c.get("text", "") for c in chunks]

        # Generate embeddings
        if self._model is not None:
            vectors = self._embed_with_model(texts)
        else:
            vectors = self._embed_with_fallback(texts)

        # Build result
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "chunk_id": chunk.get("chunk_id"),
                "vector": vectors[i],
                "dimensions": len(vectors[i]),
                "model_name": self.config.model_name if self._model else "hash-fallback",
            })

        return result

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        self._ensure_initialized()

        if self._model is not None:
            return self._embed_with_model([text])[0]
        else:
            return self._embed_with_fallback([text])[0]

    def _embed_with_model(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using sentence-transformers model."""
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=self.config.normalize,
            show_progress_bar=False,
        )
        return [emb.tolist() for emb in embeddings]

    def _embed_with_fallback(self, texts: list[str]) -> list[list[float]]:
        """
        Generate deterministic embeddings using hashing.

        This is a fallback for when sentence-transformers is not available.
        This is not a replacement for real semantic embeddings, but it is:
        - deterministic (test-friendly)
        - offline (no model downloads required)
        - "good enough" to keep retrieval pipeline logic testable
        """
        vectors = []
        for text in texts:
            vector = self._hash_to_vector(text, self.config.dimensions)
            vectors.append(vector)
        return vectors

    def _hash_to_vector(self, text: str, dimensions: int) -> list[float]:
        """
        Convert text to a deterministic vector via token hashing.

        Uses a simple bag-of-words style hashing trick so that texts that share
        meaningful tokens (e.g., analyte names, values, units) produce vectors
        with higher cosine similarity.
        """
        token_re = re.compile(r"[a-z0-9]+", re.IGNORECASE)
        stopwords = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "been",
            "being",
            "by",
            "for",
            "from",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "that",
            "the",
            "these",
            "this",
            "those",
            "to",
            "was",
            "were",
            "with",
            "within",
            "which",
        }

        tokens = [t.lower() for t in token_re.findall(text)]
        filtered = [t for t in tokens if t not in stopwords]
        if filtered:
            tokens = filtered

        vector = [0.0] * dimensions

        # Unigram features
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % dimensions
            vector[idx] += 1.0

        # Bigram features (lighter weight) improve robustness for short texts.
        for t1, t2 in zip(tokens, tokens[1:]):
            digest = hashlib.sha256(f"{t1}_{t2}".encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % dimensions
            vector[idx] += 0.5

        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector

    def vector_to_blob(self, vector: list[float]) -> bytes:
        """
        Convert vector to binary blob for storage.

        Args:
            vector: List of floats

        Returns:
            Binary blob (float32 per element)
        """
        return struct.pack(f'{len(vector)}f', *vector)

    def blob_to_vector(self, blob: bytes) -> list[float]:
        """
        Convert binary blob back to vector.

        Args:
            blob: Binary blob from vector_to_blob

        Returns:
            List of floats
        """
        num_floats = len(blob) // 4
        return list(struct.unpack(f'{num_floats}f', blob))

    def cosine_similarity(
        self,
        vector1: list[float],
        vector2: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Similarity score in range [-1, 1]
        """
        if len(vector1) != len(vector2):
            raise ValueError("Vectors must have same dimensions")

        dot = sum(a * b for a, b in zip(vector1, vector2))
        norm1 = sum(a * a for a in vector1) ** 0.5
        norm2 = sum(b * b for b in vector2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def find_similar(
        self,
        query_vector: list[float],
        candidates: list[tuple[str, list[float]]],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Find most similar vectors to query.

        Args:
            query_vector: Query embedding
            candidates: List of (id, vector) tuples
            top_k: Number of results to return

        Returns:
            List of (id, similarity_score) tuples, sorted by similarity
        """
        results = []
        for chunk_id, vector in candidates:
            similarity = self.cosine_similarity(query_vector, vector)
            results.append((chunk_id, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]
