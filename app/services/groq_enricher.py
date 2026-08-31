"""
Groq-powered job description enrichment.

Groq is used as a semantic enrichment layer.
The output is intentionally conservative because these fields
directly affect JobAgent ranking.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.groq_client import GroqClient


# -------------------------------------------------------------------
# Generic phrases that must NEVER become skills.
# These are responsibilities/capabilities, not concrete skills.
# -------------------------------------------------------------------

FORBIDDEN_SKILLS = {
    "debugging",
    "architecture design",
    "system design",
    "ai system design",
    "design",
    "integration",
    "integration engineering",
    "prototyping",
    "performance optimization",
    "performance engineering",
    "cost optimization",
    "reliability engineering",
    "reliability",
    "observability",
    "observability engineering",
    "operational readiness",
    "technical judgment",
    "technical leadership",
    "customer leadership",
    "customer engineering",
    "technical consulting",
    "problem solving",
    "communication",
    "stakeholder management",
    "project management",
    "program management",
    "production engineering",
    "architecture",
    "implementation",
    "deployment",
    "ai deployment",
    "model evaluation",
}


class GroqJobEnricher:
    """Extract structured job information using Groq."""

    def __init__(
        self,
        client: GroqClient | None = None,
    ) -> None:
        self.client = client or GroqClient()

    def analyze(
        self,
        *,
        title: str,
        description: str,
    ) -> dict[str, Any]:
        """
        Analyze a job description.

        Returns:
            required_skills
            preferred_skills
            experience_years
            seniority
            role_family
            job_type
            confidence
        """

        if not description.strip():
            return self._empty_result()

        prompt = self._build_prompt(
            title=title,
            description=description,
        )

        response = self.client.generate(prompt)

        return self._parse_response(response)

    # ----------------------------------------------------------------
    # Prompt
    # ----------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        *,
        title: str,
        description: str,
    ) -> str:
        return f"""
You are the semantic job-analysis engine for JobAgent.

Analyze the job posting below and return ONLY valid JSON.

Your output will be used directly by a job-matching and ranking system.
Therefore, be CONSERVATIVE and PRECISION-FIRST.

Do NOT try to make the job look more technical than it actually is.

============================================================
SKILL EXTRACTION RULES
============================================================

A skill must be a concrete technical or professional competency
that a candidate could reasonably list on a resume.

GOOD SKILL EXAMPLES:
- Python
- Java
- C++
- JavaScript
- TypeScript
- SQL
- PyTorch
- TensorFlow
- Kubernetes
- Docker
- AWS
- Azure
- GCP
- PostgreSQL
- Redis
- Kafka
- React
- FastAPI
- Django
- LangChain
- RAG
- LLMs
- machine learning
- deep learning
- NLP
- computer vision
- reinforcement learning
- information retrieval
- agent systems
- model evaluation
- evaluation systems

BAD SKILL EXAMPLES:
- debugging
- architecture design
- system design
- integration
- prototyping
- deployment
- performance optimization
- cost optimization
- reliability engineering
- observability
- operational readiness
- technical judgment
- communication
- leadership
- customer leadership
- stakeholder management
- problem solving
- implementation
- production engineering
- technical consulting

These BAD examples are responsibilities or general engineering
abilities, NOT skills.

============================================================
IMPORTANT AI/ML RULE
============================================================

AI/ML concepts ARE valid skills when they are actually required
by the job.

For example:

"build RAG systems"
-> "RAG"

"work with large language models"
-> "LLMs"

"machine learning systems"
-> "machine learning"

"retrieval systems"
-> "information retrieval"

"agentic applications"
-> "agent systems"

Do NOT create artificial compound skills such as:
- "AI system design"
- "AI deployment"
- "AI system evaluation"
- "evaluation harness development"

Prefer the underlying concrete technology or methodology.

============================================================
REQUIRED VS PREFERRED
============================================================

required_skills:
Skills explicitly required or clearly necessary for the role.

preferred_skills:
Skills explicitly described as preferred, valuable, bonus,
nice-to-have, or otherwise optional.

Do NOT put the same skill in both lists.

============================================================
EXPERIENCE
============================================================

Extract the MINIMUM years of professional experience ONLY when
the posting explicitly states a numeric requirement.

Examples:

"3+ years of experience"
-> 3

"2-4 years of experience"
-> 2

"at least 5 years"
-> 5

If no explicit numeric experience requirement exists:
-> null

Do NOT estimate experience from seniority, title, responsibilities,
or phrases such as "experienced engineer".

============================================================
ROLE FAMILY
============================================================

Choose the closest role family based primarily on the title and
actual responsibilities.

Allowed values:

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

============================================================
SENIORITY
============================================================

Return one of:

- intern
- junior
- mid
- senior
- lead
- staff
- principal
- unknown

Only infer seniority when the title or description provides
reasonable evidence.

============================================================
JOB TYPE
============================================================

Return one of:

- full-time
- part-time
- contract
- internship
- temporary
- other
- null

============================================================
OUTPUT QUALITY
============================================================

1. Prefer precision over recall.
2. Do not invent skills.
3. Do not turn responsibilities into skills.
4. Do not extract ordinary English words.
5. Do not extract company names as skills.
6. Do not extract products merely mentioned incidentally.
7. Do not extract benefits or legal requirements.
8. Use canonical/common names.
9. Keep skill lists focused.
10. Return all concrete technical skills that are genuinely relevant
    to performing the job. Do not artificially minimize the list.
11. Usually return fewer than 8 preferred skills.
12. Do not pad the list with generic engineering activities.
    However, include genuine AI/ML concepts such as LLMs, RAG,
    information retrieval, agent systems, model evaluation, etc.
    when they are clearly relevant to the role.
13. Confidence represents confidence in the overall extraction quality.

============================================================
RETURN EXACTLY THIS JSON
============================================================

{{
  "required_skills": [],
  "preferred_skills": [],
  "experience_years": null,
  "seniority": "unknown",
  "role_family": "Other",
  "job_type": null,
  "confidence": 0.0
}}

JOB TITLE:
{title}

JOB DESCRIPTION:
{description}
""".strip()

    # ----------------------------------------------------------------
    # Empty result
    # ----------------------------------------------------------------

    @staticmethod
    def _empty_result() -> dict[str, Any]:
        return {
            "required_skills": [],
            "preferred_skills": [],
            "experience_years": None,
            "seniority": "unknown",
            "role_family": "Other",
            "job_type": None,
            "confidence": 0.0,
        }

    # ----------------------------------------------------------------
    # Response parsing
    # ----------------------------------------------------------------

    @classmethod
    def _parse_response(
        cls,
        response: str,
    ) -> dict[str, Any]:
        """Safely parse Groq JSON output."""

        if not response:
            return cls._empty_result()

        cleaned = response.strip()

        # Remove accidental markdown fences.
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

    # ----------------------------------------------------------------
    # Validation / cleanup
    # ----------------------------------------------------------------

    @classmethod
    def _validate(
        cls,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and clean Groq output."""

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

        required = cls._clean_skills(
            required
        )

        preferred = cls._clean_skills(
            preferred
        )

        # A skill cannot be both required and preferred.
        preferred = [
            skill
            for skill in preferred
            if skill not in required
        ]

        # Keep lists focused.
        required = required[:12]
        preferred = preferred[:8]

        # ------------------------------------------------------------
        # Experience
        # ------------------------------------------------------------

        experience = data.get(
            "experience_years"
        )

        if experience is not None:
            try:
                experience = float(
                    experience
                )

                if experience < 0:
                    experience = None

            except (TypeError, ValueError):
                experience = None

        # ------------------------------------------------------------
        # Seniority
        # ------------------------------------------------------------

        seniority = data.get(
            "seniority"
        )

        if seniority is not None:
            seniority = str(
                seniority
            ).strip().lower()

        allowed_seniority = {
            "intern",
            "junior",
            "mid",
            "senior",
            "lead",
            "staff",
            "principal",
            "unknown",
        }

        if seniority not in allowed_seniority:
            seniority = "unknown"

        # ------------------------------------------------------------
        # Role family
        # ------------------------------------------------------------

        role_family = data.get(
            "role_family",
            "Other",
        )

        if not isinstance(
            role_family,
            str,
        ):
            role_family = "Other"

        role_family = role_family.strip()

        # ------------------------------------------------------------
        # Job type
        # ------------------------------------------------------------

        job_type = data.get(
            "job_type"
        )

        if job_type is not None:
            job_type = str(
                job_type
            ).strip().lower()

        allowed_job_types = {
            "full-time",
            "part-time",
            "contract",
            "internship",
            "temporary",
            "other",
        }

        if job_type not in allowed_job_types:
            job_type = None

        # ------------------------------------------------------------
        # Confidence
        # ------------------------------------------------------------

        confidence = data.get(
            "confidence",
            0.0,
        )

        try:
            confidence = float(
                confidence
            )
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

    # ----------------------------------------------------------------
    # Skill cleanup
    # ----------------------------------------------------------------

    @classmethod
    def _clean_skills(
        cls,
        skills: list[Any],
    ) -> list[str]:
        """
        Clean, deduplicate, and reject obvious non-skills.

        This is a second safety layer after the LLM prompt.
        """

        cleaned: list[str] = []
        seen: set[str] = set()

        for skill in skills:
            if skill is None:
                continue

            value = str(skill).strip().lower()

            if not value:
                continue

            # Normalize whitespace.
            value = re.sub(
                r"\s+",
                " ",
                value,
            )

            # Reject generic/non-skill phrases.
            if value in FORBIDDEN_SKILLS:
                continue

            # Reject extremely long generated phrases.
            if len(value) > 60:
                continue

            # Reject obvious sentence-like outputs.
            if value.endswith(
                (".", ",", ";", ":")
            ):
                continue

            if value not in seen:
                seen.add(value)
                cleaned.append(value)

        return cleaned