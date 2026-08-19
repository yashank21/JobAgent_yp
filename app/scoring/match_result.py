"""
Legacy compatibility wrapper.

The authoritative scoring engine is final_scorer.py.
This module exists only so older tests/imports continue working.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.match import JobMatch
from app.scoring.final_scorer import score_job


def calculate_match(
    candidate: CandidateProfile,
    job: Job,
) -> JobMatch:
    """
    Backward-compatible wrapper around the V2 scoring engine.
    """
    return score_job(candidate, job)