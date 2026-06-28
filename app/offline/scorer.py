import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from app.config import settings
from app.offline.schemas import ParsedJD, ScoringResult


class Scorer:
    def __init__(self) -> None:
        self._llm: Optional[object] = None

    @property
    def llm(self) -> object:
        if self._llm is None:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=str(settings.llm_model_path),
                n_ctx=settings.llm_context_size,
                max_tokens=settings.llm_max_tokens,
                n_threads=settings.llm_threads,
                verbose=False,
            )
        return self._llm

    def score(
        self,
        resume_text: str,
        jd: ParsedJD,
        profile_id: str,
    ) -> ScoringResult:
        prompt = f"""You are an expert technical recruiter. Evaluate how well the following RESUME matches the JOB DESCRIPTION.

Return ONLY valid JSON with these fields:
- "skill_score": 0-100 (how well required skills are met)
- "experience_score": 0-100 (how well years/type of experience matches)
- "education_score": 0-100 (how well education requirements are met)
- "behavioral_score": 0-100 (cultural fit, communication, leadership signals)
- "explanation": a 1-3 sentence summary of strengths and gaps

JOB DESCRIPTION:
Required Skills: {', '.join(jd.required_skills)}
Preferred Skills: {', '.join(jd.preferred_skills)}
Min Experience Years: {jd.min_experience_years}
Education Required: {jd.education_required}
Responsibilities: {' | '.join(jd.responsibilities)}

RESUME TEXT:
{resume_text[:3000]}

JSON response:"""
        output = self.llm(prompt, echo=False)
        raw = output.get("choices", [{}])[0].get("text", "").strip()

        data = self._try_parse_json(raw)
        if data is None:
            return ScoringResult(
                skill_score=0.0,
                experience_score=0.0,
                education_score=0.0,
                behavioral_score=0.0,
                composite_score=0.0,
                explanation=f"LLM parse failed — raw: {raw[:200]}",
            )

        skill = max(0.0, min(100.0, float(data.get("skill_score", 0))))
        exp = max(0.0, min(100.0, float(data.get("experience_score", 0))))
        edu = max(0.0, min(100.0, float(data.get("education_score", 0))))
        beh = max(0.0, min(100.0, float(data.get("behavioral_score", 0))))

        composite = (
            settings.skill_weight * skill
            + settings.experience_weight * exp
            + settings.education_weight * edu
            + settings.behavioral_weight * beh
        )

        return ScoringResult(
            skill_score=round(skill, 1),
            experience_score=round(exp, 1),
            education_score=round(edu, 1),
            behavioral_score=round(beh, 1),
            composite_score=round(composite, 1),
            explanation=str(data.get("explanation", "")),
        )

    @staticmethod
    def _try_parse_json(raw: str) -> Optional[dict]:
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None
