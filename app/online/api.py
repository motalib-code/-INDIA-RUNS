from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.offline.nlp import extract_jd
from app.offline.parser import extract_text_from_pdf
from app.offline.pipeline import CortexRankPipeline

app = FastAPI(title="CortexRank API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = CortexRankPipeline()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "index_built": pipeline.built,
    }


@app.post("/index/build")
def build_index() -> dict:
    try:
        pipeline.build_index_from_dir()
        return {"status": "ok", "count": pipeline.indexer.size}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/index/load")
def load_index() -> dict:
    try:
        pipeline.load_index()
        return {"status": "ok", "count": pipeline.indexer.size}
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/search/pdf")
async def search_pdf(file: UploadFile = File(...)) -> list[dict]:
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    temp = settings.data_dir / "_upload_jd.pdf"
    content = await file.read()
    temp.write_bytes(content)

    jd_text = extract_text_from_pdf(temp)
    jd = extract_jd(jd_text)
    temp.unlink(missing_ok=True)

    try:
        results = pipeline.search(jd_text, jd)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [_serialize(meta, score) for meta, score in results]


@app.post("/search/text")
def search_text(jd_text: str) -> list[dict]:
    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="Empty JD text")

    jd = extract_jd(jd_text)

    try:
        results = pipeline.search(jd_text, jd)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [_serialize(meta, score) for meta, score in results]


def _serialize(meta, score) -> dict:
    return {
        "profile_id": meta.id,
        "name": meta.name,
        "skills": meta.skills_text,
        "composite_score": score.composite_score,
        "skill_score": score.skill_score,
        "experience_score": score.experience_score,
        "education_score": score.education_score,
        "behavioral_score": score.behavioral_score,
        "explanation": score.explanation,
    }
