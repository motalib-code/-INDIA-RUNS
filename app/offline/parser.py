from pathlib import Path

from PyPDF2 import PdfReader

from app.offline.schemas import ParsedResume, ParsedJD


def parse_resume_pdf(path: Path) -> ParsedResume:
    reader = PdfReader(str(path))
    raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return ParsedResume(raw_text=raw_text.strip())


def parse_jd_pdf(path: Path) -> ParsedJD:
    reader = PdfReader(str(path))
    raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return ParsedJD(raw_text=raw_text.strip())


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
