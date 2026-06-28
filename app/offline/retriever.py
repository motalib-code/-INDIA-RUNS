from typing import Optional

import numpy as np
from sentence_transformers import CrossEncoder

from app.config import settings
from app.offline.indexer import TextIndexer


class Retriever:
    def __init__(self, indexer: TextIndexer) -> None:
        self._indexer = indexer
        self._cross_encoder: Optional[CrossEncoder] = None

    @property
    def cross_encoder(self) -> CrossEncoder:
        if self._cross_encoder is None:
            self._cross_encoder = CrossEncoder(
                str(settings.cross_encoder_model)
            )
        return self._cross_encoder

    def retrieve(
        self,
        query: str,
        blend_factor: float = 0.5,
    ) -> list[tuple[int, float]]:
        hybrid = self._indexer.hybrid_search(query, settings.top_k_rerank)
        if not hybrid:
            return []

        idxs = [h[0] for h in hybrid]
        texts = [self._indexer._raw_texts[i] for i in idxs]

        pairs = [(query, t) for t in texts]
        ce_scores = self.cross_encoder.predict(pairs, show_progress_bar=False)

        if isinstance(ce_scores[0], np.ndarray):
            ce_scores = [s[1] for s in ce_scores]

        rrf_map = dict(hybrid)
        ce_min, ce_max = float(min(ce_scores)), float(max(ce_scores))
        ce_range = ce_max - ce_min if ce_max > ce_min else 1.0

        blended: list[tuple[int, float]] = []
        for i, idx in enumerate(idxs):
            rrf_norm = rrf_map.get(idx, 0.0)
            ce_norm = (float(ce_scores[i]) - ce_min) / ce_range
            blended.append((idx, blend_factor * ce_norm + (1 - blend_factor) * rrf_norm))

        blended.sort(key=lambda x: x[1], reverse=True)
        return blended[: settings.top_k_final]
