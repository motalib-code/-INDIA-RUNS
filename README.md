# CortexRank

**AI-powered resume screening and ranking system** using hybrid retrieval (FAISS + BM25), cross-encoder re-ranking, and LLM-generated fit summaries.

## Architecture

```
resume_search_engine/
├── app/
│   ├── config.py            # Pydantic Settings — all paths, models, scoring weights
│   ├── offline/
│   │   ├── pipeline.py      # CortexRankPipeline — build/load index, search
│   │   ├── indexer.py       # FAISS + BM25 index builders
│   │   ├── retriever.py     # Hybrid retrieval (dense + sparse)
│   │   ├── scorer.py        # Cross-encoder re-ranking + weighted scoring
│   │   ├── nlp.py           # Skill extraction, experience parsing
│   │   ├── parser.py        # PDF text extraction
│   │   └── schemas.py       # Pydantic models
│   ├── online/
│   │   └── api.py           # FastAPI REST API
│   └── frontend/
│       └── app.py           # Streamlit UI
├── tests/
├── data/                    # Indices + metadata (gitignored)
├── models/                  # Downloaded LLM files (gitignored)
└── requirements.txt
```

## How It Works

1. **Parse** — PDF resumes are converted to text via `parser.py`
2. **Index** — Text is chunked and embedded with `all-MiniLM-L6-v2` into a FAISS index; skill keywords are indexed in a BM25 index
3. **Retrieve** — Given a job description, top-K candidates are retrieved from both FAISS (semantic similarity) and BM25 (keyword match), then fused via Reciprocal Rank Fusion
4. **Re-rank** — Retrieved candidates are scored with a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for fine-grained relevance
5. **Score** — Weighted combination of skill match, experience, education, and behavioral scores produces a final rank
6. **Summarize** — Mistral 7B (GGUF, via llama-cpp-python) generates a per-resume fit summary

## Scoring Weights

| Factor   | Weight |
|----------|--------|
| Skills   | 0.45   |
| Experience | 0.30  |
| Education  | 0.15  |
| Behavioral| 0.10   |

Configurable via `config.py` → `SCORING_WEIGHTS`.

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Model Files

Place your Mistral 7B GGUF model in `models/`:

```
models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

Download from [TheBloke on HuggingFace](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF).

## Running

```bash
# Start the API server
uvicorn app.online.api:app --reload --host 0.0.0.0 --port 8000

# Start the Streamlit frontend (separate terminal)
streamlit run app/frontend/app.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | API health check |
| `POST` | `/index/build` | Build index from a directory of PDFs |
| `POST` | `/index/load` | Load a pre-built index from disk |
| `POST` | `/search/pdf` | Upload resume PDF + JD for ranking |
| `POST` | `/search/text` | Paste resume text + JD for ranking |

### Example: Search by text

```bash
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "5 years Python experience, ML background...",
    "job_description": "Looking for senior ML engineer..."
  }'
```

## Frontend

Streamlit app at `http://localhost:8501`:

- **Sidebar** — Build/load index, view health status
- **Tab 1** — Upload PDF resume + paste JD
- **Tab 2** — Paste resume text + JD
- **Results** — Ranked candidates with fit scores, Plotly charts, LLM summaries

## Configuration

All settings live in `app/config.py`:

```python
# paths
DATA_DIR = "data"
FAISS_INDEX_PATH = "data/faiss_index.bin"
BM25_INDEX_PATH = "data/bm25_index.pkl"

# models
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MODEL_PATH = "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

# retrieval
TOP_K = 20
RRF_K = 60
```

Override via environment variables or `.env`.

## License

MIT
