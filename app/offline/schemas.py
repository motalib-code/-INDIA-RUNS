from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ParsedResume:
    raw_text: str
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)


@dataclass
class ParsedJD:
    raw_text: str
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_experience_years: int = 0
    education_required: str = ""
    responsibilities: list[str] = field(default_factory=list)


@dataclass
class ProfileMetadata:
    id: str
    name: str
    file_path: str
    skills_text: str
    experience_text: str
    education_text: str


@dataclass
class IndexData:
    metadata: list[ProfileMetadata]
    faiss_index_path: str
    bm25_index_path: str
