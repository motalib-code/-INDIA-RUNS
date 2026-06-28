from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    project_root: Path = Path(__file__).resolve().parent.parent

    data_dir: Path = project_root / "data"
    models_dir: Path = project_root / "models"

    sample_resumes_dir: Path = data_dir / "sample_resumes"
    jd_samples_dir: Path = data_dir / "jd_samples"
    faiss_index_path: Path = data_dir / "faiss_index.bin"
    bm25_index_path: Path = data_dir / "bm25_index.pkl"
    metadata_path: Path = data_dir / "metadata.json"

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    llm_model_path: Path = models_dir / "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    llm_context_size: int = 2048
    llm_max_tokens: int = 512
    llm_threads: int = 4

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "cortexrank"

    faiss_ef_construction: int = 200
    faiss_ef_search: int = 64
    faiss_m: int = 32

    rrf_k: int = 60
    top_k_retrieve: int = 200
    top_k_score: int = 100
    top_k_rerank: int = 20
    top_k_final: int = 10

    skill_weight: float = 0.40
    experience_weight: float = 0.25
    education_weight: float = 0.15
    behavioral_weight: float = 0.20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
