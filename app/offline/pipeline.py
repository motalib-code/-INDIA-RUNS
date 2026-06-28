from pathlib import Path
from typing import Optional

from app.config import settings
from app.offline.indexer import TextIndexer
from app.offline.nlp import extract_jd, extract_resume
from app.offline.parser import extract_text_from_pdf
from app.offline.retriever import Retriever
from app.offline.scorer import Scorer
from app.offline.schemas import ParsedJD, ParsedResume, ProfileMetadata, ScoringResult


class CortexRankPipeline:
    def __init__(self) -> None:
        self.indexer = TextIndexer()
        self.retriever: Optional[Retriever] = None
        self.scorer = Scorer()
        self._built = False

    def build_index_from_dir(
        self, resumes_dir: Optional[Path] = None
    ) -> None:
        src = resumes_dir or settings.sample_resumes_dir
        if not src.exists():
            raise FileNotFoundError(f"Resumes directory not found: {src}")
        pdfs = sorted(src.glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(f"No PDFs found in {src}")

        metadata: list[ProfileMetadata] = []
        for pdf_path in pdfs:
            text = extract_text_from_pdf(pdf_path)
            parsed = extract_resume(text)
            meta = ProfileMetadata(
                id=pdf_path.stem,
                name=parsed.name or pdf_path.stem,
                file_path=str(pdf_path),
                skills_text=", ".join(parsed.skills),
                experience_text=" ".join(parsed.experience),
                education_text=" ".join(parsed.education),
            )
            metadata.append(meta)

        self.indexer.build(metadata)
        self.indexer.save()
        self.retriever = Retriever(self.indexer)
        self._built = True

    def load_index(self) -> None:
        self.indexer.load()
        self.retriever = Retriever(self.indexer)
        self._built = True

    def search(self, jd_text: str, jd: Optional[ParsedJD] = None) -> list[tuple[ProfileMetadata, ScoringResult]]:
        if not self._built or self.retriever is None:
            raise RuntimeError("Index not built or loaded — call build_index_from_dir() or load_index() first")

        if jd is None:
            jd = extract_jd(jd_text)

        query = " ".join(jd.required_skills)
        if jd.responsibilities:
            query += " " + " ".join(jd.responsibilities)

        ranked = self.retriever.retrieve(query)

        results: list[tuple[ProfileMetadata, ScoringResult]] = []
        for idx, score in ranked:
            meta = self.indexer.metadata[idx]
            resume_text = self.indexer._raw_texts[idx]
            scoring = self.scorer.score(resume_text, jd, meta.id)
            results.append((meta, scoring))

        results.sort(key=lambda x: x[1].composite_score, reverse=True)
        return results[: settings.top_k_final]

    @property
    def built(self) -> bool:
        return self._built
