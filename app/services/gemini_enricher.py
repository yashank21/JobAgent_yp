"""
Gemini-powered job description enrichment.

Gemini is used as a semantic fallback/enrichment layer.
Deterministic parsers remain the primary source of truth.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.gemini_client import GeminiClient


class GeminiJobEnricher:
    """Extract structured job information using Gemini."""

    def __init__(
        self,
        client: GeminiClient | None = None,
    ) -> None:
        self.client = client or GeminiClient()

    def analyze(
        self,
        *,
        title: str,
        description: str,
    ) -> dict[str, Any]:
        """
        Analyze a job description.

        Returns a normalized dictionary containing:
        - required_skills
        - preferred_skills
        - experience_years
        - seniority
        - role_family
        - job_type
        - confidence
        """

        if not description.strip():
            return self._empty_result()

        prompt = self._build_prompt(
            title=title,
            description=description,
        )

        response = self.client.generate(prompt)

        return self._parse_response(response)

    @staticmethod
    def _build_prompt(
        *,
        title: str,
        description: str,
    ) -> str:
        return f"""
You are the semantic job-analysis engine for JobAgent.

Analyze the following job posting and return ONLY valid JSON.

Your job is to identify actual job requirements, not arbitrary words
that happen to appear in the description.

CRITICAL RULES:

1. Only include genuine technical/professional skills.
2. Do NOT treat ordinary English words as skills.
   Example: "visit our website" must NOT produce "visit".
3. Distinguish required skills from preferred/nice-to-have skills.
4. Extract the minimum years of professional experience if explicitly
   stated.
5. If experience is ambiguous or absent, use null.
6. Identify the actual role family from the job title and description.
7. Ignore benefits, company marketing, legal text, and unrelated words.
8. Do not infer a skill merely because it is mentioned incidentally.
9. Return canonical/common skill names where possible.
10. Confidence must represent confidence in the overall extraction.

Allowed role_family examples:

- Software Engineer
- Backend Engineer
- Frontend Engineer
- Full Stack Engineer
- AI Engineer
- Machine Learning Engineer
- Data Scientist
- Data Engineer
- DevOps Engineer
- Cloud Engineer
- SRE
- Security Engineer
- QA Engineer
- Mobile Engineer
- Product Manager
- Data Analyst
- Solutions Engineer
- Technical Architect
- Engineering Manager
- Other

Return exactly this JSON structure:

{{
  "required_skills": [],
  "preferred_skills": [],
  "experience_years": null,
  "seniority": null,
  "role_family": "Other",
  "job_type": null,
  "confidence": 0.0
}}

JOB TITLE:
{title}

JOB DESCRIPTION:
{description}
""".strip()

    @staticmethod
    def _empty_result() -> dict[str, Any]:
        return {
            "required_skills": [],
            "preferred_skills": [],
            "experience_years": None,
            "seniority": None,
            "role_family": "Other",
            "job_type": None,
            "confidence": 0.0,
        }

    @classmethod
    def _parse_response(
        cls,
        response: str,
    ) -> dict[str, Any]:
        """Safely parse Gemini's JSON response."""

        if not response:
            return cls._empty_result()

        cleaned = response.strip()

        # Handle accidental markdown fences.
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try extracting the first JSON object.
            match = re.search(
                r"\{.*\}",
                cleaned,
                flags=re.DOTALL,
            )

            if not match:
                return cls._empty_result()

            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return cls._empty_result()

        if not isinstance(data, dict):
            return cls._empty_result()

        return cls._validate(data)

    @classmethod
    def _validate(
        cls,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate Gemini output before JobAgent consumes it."""

        required = data.get(
            "required_skills",
            [],
        )

        preferred = data.get(
            "preferred_skills",
            [],
        )

        if not isinstance(required, list):
            required = []

        if not isinstance(preferred, list):
            preferred = []

        required = [
            str(skill).strip().lower()
            for skill in required
            if str(skill).strip()
        ]

        preferred = [
            str(skill).strip().lower()
            for skill in preferred
            if str(skill).strip()
        ]

        experience = data.get(
            "experience_years"
        )

        if experience is not None:
            try:
                experience = float(experience)

                if experience < 0:
                    experience = None

            except (TypeError, ValueError):
                experience = None

        seniority = data.get("seniority")

        if seniority is not None:
            seniority = str(
                seniority
            ).strip().lower()

        role_family = data.get(
            "role_family",
            "Other",
        )

        if not isinstance(
            role_family,
            str,
        ):
            role_family = "Other"

        job_type = data.get("job_type")

        if job_type is not None:
            job_type = str(
                job_type
            ).strip().lower()

        confidence = data.get(
            "confidence",
            0.0,
        )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        return {
            "required_skills": required,
            "preferred_skills": preferred,
            "experience_years": experience,
            "seniority": seniority,
            "role_family": role_family,
            "job_type": job_type,
            "confidence": confidence,
        }