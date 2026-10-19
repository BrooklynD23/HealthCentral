"""
Embeddings Module for RAG Pipeline.

Generates vector embeddings for text chunks using local models.
Supports caching and batch processing for efficiency.
"""

import hashlib
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# Source for the one-time, user-run fetch only (scripts/download_models.py
# embedding). The runtime below never contacts this repo.
EMBEDDING_REPO_ID = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
# One sha256 per fetched file, measured on a bundle fetched at EMBEDDING_REVISION.
# Only scripts/download_models.py hashes; the runtime load path does not.
EMBEDDING_FILE_SHA256: dict[str, str] = {
    "1_Pooling/config.json": "4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23",
    "README.md": "dcd602d2fd35c203a247304a06fec6654a12f7941b739f9221a064fe8dc3b7f0",
    "config.json": "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
    "config_sentence_transformers.json": "061ca9d39661d6c6d6de5ba27f79a1cd5770ea247f8d46412a68a498dc5ac9f3",
    "model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    "modules.json": "84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf",
    "sentence_bert_config.json": "fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7",
    "special_tokens_map.json": "303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
    "tokenizer_config.json": "acb92769e8195aabd29b7b2137a9e6d6e25c476a4f15aa4355c233426c61576b",
    "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
}
EMBEDDING_FILES = tuple(EMBEDDING_FILE_SHA256)
_BACKEND_DIR = Path(__file__).resolve().parents[1]


class EmbeddingModelUnavailableError(RuntimeError):
    """The bundled embedding model is missing or cannot be loaded offline."""


def resolve_embedding_model_dir() -> Path:
    """Directory the embedding model is loaded from (EMBEDDING_MODEL_PATH)."""
    from core.config import settings

    path = Path(settings.embedding_model_path)
    return path if path.is_absolute() else _BACKEND_DIR / path


@dataclass
class EmbeddingsConfig:
    """Configuration for embeddings generation."""
    model_name: str = EMBEDDING_MODEL_NAME
    dimensions: int = 384
    batch_size: int = 32
    normalize: bool = True


class EmbeddingsModule:
    """
    Text embedding generation for RAG retrieval.

    Loads the bundled sentence-transformers model from a local directory with
    Hugging Face offline, and fails closed (EmbeddingModelUnavailableError) when
    it is absent. The hash-based fallback exists for tests only
    (use_fallback=True); product code must never enable it (HC-EMB-003).
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        use_fallback: bool = False,
    ):
        """
        Args:
            model_name: Label stored with each vector (Embedding.model_name).
            use_fallback: Tests only. Use hash vectors when the model is absent.
        """
        self.config = EmbeddingsConfig(model_name=model_name)
        self.use_fallback = use_fallback
        self._model = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Load the local model once. A failure is not cached: the next call
        retries, so fetching the model does not need a restart."""
        if self._initialized:
            return
        try:
            self._model = self._load_local_model()
            self.config.dimensions = self._model.get_sentence_embedding_dimension()
        except EmbeddingModelUnavailableError:
            if not self.use_fallback:
                raise
            self._model = None
        self._initialized = True

    def _load_local_model(self):
        """Load from the bundled directory only; never from the network."""
        model_dir = resolve_embedding_model_dir()
        missing = [name for name in EMBEDDING_FILES if not (model_dir / name).is_file()]
        if missing:
            raise EmbeddingModelUnavailableError(
                f"Embedding model not installed "
                f"({len(missing)} of {len(EMBEDDING_FILES)} files missing). Fetch it once with: "
                "cd src/backend && python scripts/download_models.py embedding"
            )
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingModelUnavailableError("sentence-transformers is not installed") from exc
        try:
            return SentenceTransformer(str(model_dir), local_files_only=True)
        except Exception as exc:  # corrupt or incompatible files: fail closed, never download
            raise EmbeddingModelUnavailableError(
                f"Embedding model failed to load: {type(exc).__name__}"
            ) from exc

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
