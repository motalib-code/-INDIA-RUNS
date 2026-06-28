import re
from typing import Optional

import spacy
from spacy.language import Language
from spacy.tokens import Doc

from app.offline.schemas import ParsedResume, ParsedJD

SKILL_KEYWORDS: set[str] = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "gitlab ci",
    "aws", "gcp", "azure", "gke", "eks", "aks", "lambda", "ec2", "s3",
    "react", "angular", "vue", "svelte", "nextjs", "nuxt", "fastapi",
    "flask", "django", "spring boot", "node.js", "express", "gin",
    "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "spark",
    "kafka", "rabbitmq", "pulsar", "airflow", "dagster", "prefect",
    "machine learning", "deep learning", "nlp", "computer vision",
    "llm", "rag", "langchain", "llamaindex", "openai", "claude",
    "tableau", "power bi", "looker", "superset", "grafana",
    "git", "linux", "bash", "rest api", "graphql", "grpc",
}


@Language.component("skill_ner")
def _skill_ner(doc: Doc) -> Doc:
    spans = []
    lower_text = doc.text.lower()
    for skill in SKILL_KEYWORDS:
        idx = lower_text.find(skill)
        while idx != -1:
            start_char = idx
            end_char = idx + len(skill)
            span = doc.char_span(start_char, end_char, label="SKILL")
            if span is not None:
                spans.append(span)
            idx = lower_text.find(skill, idx + 1)
    doc.spans["skills"] = spans
    return doc


_nlp: Optional[Language] = None


def _get_nlp() -> Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", exclude=["lemmatizer", "ner"])
        if "skill_ner" not in _nlp.pipe_names:
            _nlp.add_pipe("skill_ner", before="parser")
    return _nlp


def extract_resume(text: str) -> ParsedResume:
    nlp = _get_nlp()
    doc = nlp(text)

    name = _extract_name(text)
    email = _extract_email(text)
    phone = _extract_phone(text)
    skills = sorted({ent.text for ent in doc.spans["skills"]})
    sections = _split_sections(text)
    experience = sections.get("experience", [])
    education = sections.get("education", [])

    return ParsedResume(
        raw_text=text,
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        experience=experience,
        education=education,
    )


def extract_jd(text: str) -> ParsedJD:
    nlp = _get_nlp()
    doc = nlp(text)

    required_skills = sorted({ent.text for ent in doc.spans["skills"]})
    preferred_skills: list[str] = []
    years = _extract_experience_years(text)
    education = _extract_education_required(text)
    responsibilities = _split_sections(text).get("responsibilities", [])

    return ParsedJD(
        raw_text=text,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        min_experience_years=years,
        education_required=education,
        responsibilities=responsibilities,
    )


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,15}\d")


def _extract_email(text: str) -> str:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else ""


def _extract_phone(text: str) -> str:
    m = _PHONE_RE.search(text)
    return m.group(0).strip() if m else ""


def _extract_name(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return lines[0] if lines else ""


def _extract_experience_years(text: str) -> int:
    pat = re.compile(
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
        re.IGNORECASE,
    )
    for m in pat.finditer(text):
        return int(m.group(1))
    return 0


def _extract_education_required(text: str) -> str:
    pat = re.compile(
        r"(bachelor(?:'s)?|master(?:'s)?|phd|ph\.d|b\.?tech|m\.?tech)"
        r"\s*(?:in|of|degree)?\s*(.+?)(?:\.|$)",
        re.IGNORECASE,
    )
    m = pat.search(text)
    return m.group(0).strip() if m else ""


_SECTION_HEADERS = re.compile(
    r"^(experience|work\s*experience|employment|professional\s*experience"
    r"|education|academic|qualifications?"
    r"|skills|technical\s*skills|core\s*competencies?"
    r"|projects?|achievements?|certifications?"
    r"|responsibilities|about|summary|profile"
    r")\s*:?$",
    re.IGNORECASE | re.MULTILINE,
)


def _split_sections(text: str) -> dict[str, list[str]]:
    lines = text.split("\n")
    boundary: list[int] = []
    for i, line in enumerate(lines):
        if _SECTION_HEADERS.match(line.strip()):
            boundary.append(i)
    boundary.append(len(lines))

    sections: dict[str, list[str]] = {}
    for idx in range(len(boundary) - 1):
        start = boundary[idx]
        end = boundary[idx + 1]
        header = _SECTION_HEADERS.match(lines[start].strip())
        if header:
            key = header.group(1).lower().replace(" ", "_")
            body = "\n".join(lines[start + 1 : end]).strip()
            bullets = [
                b.strip().lstrip("•-*") for b in body.split("\n") if b.strip()
            ]
            sections[key] = bullets
    return sections
