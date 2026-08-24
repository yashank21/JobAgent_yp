"""
Run dataset diagnostics against the saved dataset.

Does NOT collect jobs from external sources.
"""

from app.config.candidate_profile import CANDIDATE_PROFILE
from app.reporting.dataset_diagnostic import (
    analyze_dataset,
    print_diagnostic_report,
)
from app.storage.job_storage import load_jobs


def main() -> None:

    print("Loading saved dataset...")

    jobs = load_jobs()

    print(
        f"Loaded {len(jobs)} jobs."
    )

    print(
        "Running dataset diagnostic..."
    )

    report = analyze_dataset(
        candidate=CANDIDATE_PROFILE,
        jobs=jobs,
    )

    print_diagnostic_report(
        report
    )


if __name__ == "__main__":
    main()