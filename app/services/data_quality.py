"""Measurements for normalized job-data quality."""

from dataclasses import dataclass, field
from statistics import mean, median
from collections import Counter, defaultdict

from app.models.job import Job


def _percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "NOT MEASURABLE"
    return f"{numerator}/{denominator} ({numerator / denominator * 100:.1f}%)"


@dataclass
class SourceQuality:
    source: str
    jobs_analyzed: int
    normalized_jobs: int
    descriptions_present: int
    descriptions_absent: int
    retrieval_failures: int
    description_lengths: list[int]
    skills_extracted: int
    skills_none_found: int
    experience_extracted: int
    experience_none_found: int
    _jobs_by_quality_class: list[Job] = field(default_factory=list, repr=False)

    @property
    def minimum_description_length(self) -> int | None:
        return min(self.description_lengths) if self.description_lengths else None

    @property
    def maximum_description_length(self) -> int | None:
        return max(self.description_lengths) if self.description_lengths else None

    @property
    def quality_classes(self) -> dict[str, int]:
        return dict(
            Counter(
                quality_class(job)
                for job in self._jobs_by_quality_class
            )
        )

    @property
    def average_description_length(self) -> float | None:
        return mean(self.description_lengths) if self.description_lengths else None

    @property
    def median_description_length(self) -> float | None:
        return median(self.description_lengths) if self.description_lengths else None

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "jobs_analyzed": self.jobs_analyzed,
            "normalized_jobs": self.normalized_jobs,
            "descriptions_present": self.descriptions_present,
            "descriptions_absent": self.descriptions_absent,
            "retrieval_failures": self.retrieval_failures,
            "description_lengths": list(self.description_lengths),
            "skills_extracted": self.skills_extracted,
            "skills_none_found": self.skills_none_found,
            "experience_extracted": self.experience_extracted,
            "experience_none_found": self.experience_none_found,
            "minimum_description_length": self.minimum_description_length,
            "maximum_description_length": self.maximum_description_length,
        }


def quality_class(job: Job) -> str:
    """Classify a normalized job without consulting scoring or eligibility."""
    if job.description_status == "retrieval_failed":
        return "D - retrieval failure"
    if job.description_status != "present":
        return "C - JD unavailable"
    if job.skills_status == "extracted" and job.experience_status == "extracted":
        return "A - complete"
    if job.skills_status == "extracted" or job.experience_status == "extracted":
        return "B - partial extraction"
    return "B - JD present, no recognized fields"


def measure_source_quality(jobs: list[Job]) -> dict[str, SourceQuality]:
    """Aggregate quality measurements from normalized jobs before ranking."""
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[job.source or "unknown"].append(job)

    reports = {}
    for source, source_jobs in sorted(grouped.items()):
        descriptions_present = sum(
            job.description_status == "present" for job in source_jobs
        )
        report = SourceQuality(
            source=source,
            jobs_analyzed=len(source_jobs),
            normalized_jobs=len(source_jobs),
            descriptions_present=descriptions_present,
            descriptions_absent=sum(
                job.description_status == "absent" for job in source_jobs
            ),
            retrieval_failures=sum(
                job.description_status == "retrieval_failed" for job in source_jobs
            ),
            description_lengths=[
                job.description_length
                for job in source_jobs
                if job.description_status == "present"
            ],
            skills_extracted=sum(
                job.skills_status == "extracted" for job in source_jobs
            ),
            skills_none_found=sum(
                job.skills_status == "none_found" for job in source_jobs
            ),
            experience_extracted=sum(
                job.experience_status == "extracted" for job in source_jobs
            ),
            experience_none_found=sum(
                job.experience_status == "none_found" for job in source_jobs
            ),
        )
        report._jobs_by_quality_class = source_jobs
        reports[source] = report
    return reports


def render_quality_report(jobs: list[Job]) -> str:
    """Render denominator-safe human-readable measurements."""
    reports = measure_source_quality(jobs)
    lines = ["JOB DATA QUALITY REPORT", "=======================", ""]
    for report in reports.values():
        lines.extend([
            f"SOURCE: {report.source}",
            f"Jobs analyzed: {report.jobs_analyzed}",
            f"Normalized jobs: {report.normalized_jobs}",
            f"JD present: {_percentage(report.descriptions_present, report.jobs_analyzed)}",
            f"JD absent: {_percentage(report.descriptions_absent, report.jobs_analyzed)}",
            f"Retrieval failures: {_percentage(report.retrieval_failures, report.jobs_analyzed)}",
            f"Skills extracted: {_percentage(report.skills_extracted, report.jobs_analyzed)}",
            f"No recognized skills: {_percentage(report.skills_none_found, report.jobs_analyzed)}",
            f"Experience extracted: {_percentage(report.experience_extracted, report.jobs_analyzed)}",
            f"No experience found: {_percentage(report.experience_none_found, report.jobs_analyzed)}",
            f"Average JD length: {report.average_description_length if report.average_description_length is not None else 'NOT MEASURABLE'}",
            f"Median JD length: {report.median_description_length if report.median_description_length is not None else 'NOT MEASURABLE'}",
            f"Minimum JD length: {report.minimum_description_length if report.minimum_description_length is not None else 'NOT MEASURABLE'}",
            f"Maximum JD length: {report.maximum_description_length if report.maximum_description_length is not None else 'NOT MEASURABLE'}",
            "Quality classes:",
            *[
                f"  {name}: {count}/{report.jobs_analyzed}"
                for name, count in report.quality_classes.items()
            ],
            "",
        ])
    return "\n".join(lines)