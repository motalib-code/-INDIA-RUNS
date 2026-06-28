import json
import pickle
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.offline.schemas import ProfileMetadata


class TextIndexer:
    def __init__(self) -> None:
        self._encoder: Optional[SentenceTransformer] = None
        self._metadata: list[ProfileMetadata] = []
        self._raw_texts: list[str] = []
        self._embeddings: Optional[np.ndarray] = None
        self._faiss_index: Optional[faiss.Index] = None
        self._bm25: Optional[BM25Okapi] = None
        self._tokenized: list[list[str]] = []

    @property
    def encoder(self) -> SentenceTransformer:
        if self._encoder is None:
            self._encoder = SentenceTransformer(str(settings.embedding_model))
        return self._encoder

    def _tokenize(self, text: str) -> list[str]:
        return text.lower().split()

    def _index_texts(self, metadata: list[ProfileMetadata]) -> list[str]:
        parts = []
        for m in metadata:
            txt = f"{m.skills_text} {m.experience_text} {m.education_text}"
            parts.append(txt)
        return parts

    def build(self, metadata: list[ProfileMetadata]) -> None:
        self._metadata = metadata
        self._raw_texts = self._index_texts(metadata)

        self._tokenized = [self._tokenize(t) for t in self._raw_texts]

        self._bm25 = BM25Okapi(self._tokenized)

        self._embeddings = self.encoder.encode(
            self._raw_texts, show_progress_bar=True, normalize_embeddings=True
        ).astype(np.float32)

        dim = self._embeddings.shape[1]
        self._faiss_index = faiss.IndexHNSWFlat(dim, settings.faiss_m)
        self._faiss_index.hnsw.efConstruction = settings.faiss_ef_construction
        self._faiss_index.hnsw.efSearch = settings.faiss_ef_search
        self._faiss_index.add(self._embeddings)

    def save(self) -> None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)

        if self._faiss_index is not None:
            faiss.write_index(self._faiss_index, str(settings.faiss_index_path))
        else:
            raise RuntimeError("FAISS index not built — call build() first")

        if self._bm25 is not None:
            bm25_data = {
                "corpus": self._tokenized,
                "idf": self._bm25.idf,
                "doc_freq": self._bm25.doc_freq,
                "doc_len": self._bm25.doc_len,
                "avgdl": self._bm25.avgdl,
            }
            with open(str(settings.bm25_index_path), "wb") as f:
                pickle.dump(bm25_data, f)
        else:
            raise RuntimeError("BM25 index not built — call build() first")

        meta_list = [m.__dict__ for m in self._metadata]
        with open(str(settings.metadata_path), "w") as f:
            json.dump(meta_list, f, indent=2)

    def load(self) -> None:
        if not settings.faiss_index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {settings.faiss_index_path}"
            )
        self._faiss_index = faiss.read_index(str(settings.faiss_index_path))
        self._faiss_index.hnsw.efSearch = settings.faiss_ef_search

        if not settings.bm25_index_path.exists():
            raise FileNotFoundError(
                f"BM25 index not found at {settings.bm25_index_path}"
            )
        with open(str(settings.bm25_index_path), "rb") as f:
            bm25_data = pickle.load(f)
        self._tokenized = bm25_data["corpus"]
        self._raw_texts = [" ".join(t) for t in self._tokenized]
        self._bm25 = BM25Okapi(self._tokenized)
        self._bm25.idf = bm25_data["idf"]
        self._bm25.doc_freq = bm25_data["doc_freq"]
        self._bm25.doc_len = bm25_data["doc_len"]
        self._bm25.avgdl = bm25_data["avgdl"]

        if not settings.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata not found at {settings.metadata_path}"
            )
        with open(str(settings.metadata_path)) as f:
            meta_list = json.load(f)
        self._metadata = [ProfileMetadata(**m) for m in meta_list]

    def search_bm25(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        if self._bm25 is None:
            raise RuntimeError("BM25 index not loaded")
        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in top_indices]

    def search_dense(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        if self._faiss_index is None:
            raise RuntimeError("FAISS index not loaded")
        q_vec = self.encoder.encode(
            [query], normalize_embeddings=True
        ).astype(np.float32)
        distances, indices = self._faiss_index.search(q_vec, top_k)
        return [
            (int(indices[0][i]), float(distances[0][i]))
            for i in range(len(indices[0]))
        ]

    def rrf_fusion(
        self,
        dense_results: list[tuple[int, float]],
        bm25_results: list[tuple[int, float]],
        rrf_k: int = 60,
    ) -> list[tuple[int, float]]:
        scores: dict[int, float] = {}
        for rank, (idx, _) in enumerate(dense_results):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        for rank, (idx, _) in enumerate(bm25_results):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def hybrid_search(
        self, query: str, top_k: int = 50
    ) -> list[tuple[int, float]]:
        dense = self.search_dense(query, top_k)
        bm25 = self.search_bm25(query, top_k)
        return self.rrf_fusion(dense, bm25, rrf_k=settings.rrf_k)

    @property
    def metadata(self) -> list[ProfileMetadata]:
        return self._metadata

    @property
    def size(self) -> int:
        return len(self._metadata)
