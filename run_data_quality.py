"""Collect a bounded normalized dataset and report extraction quality."""

import argparse
import json

from app.collectors.universal_racer import UniversalATSRacer
from app.collectors.wellfound import WellfoundCollector
from app.services.data_quality import render_quality_report
from app.services.http_client import HTTPClient
from app.services.company_loader import load_companies_from_file

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=["greenhouse", "lever", "ashby", "workday", "wellfound", "all"],
        default="all",
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--companies-file", default="companies.txt")
    parser.add_argument("--samples-output")
    args = parser.parse_args()

    client = HTTPClient()
    jobs = []
    if args.source != "wellfound":
        racer = UniversalATSRacer(
            load_companies_from_file(args.companies_file),
            client,
            source=None if args.source == "all" else args.source,
        )
        jobs.extend(racer.collect_all())
    if args.source in ("all", "wellfound"):
        jobs.extend(WellfoundCollector(http_client=client).collect())

    selected = jobs[: max(args.sample_size, 0)]
    print(f"Requested sample: {args.sample_size}")
    print(f"Returned: {len(jobs)}")
    print(f"Normalized: {len(jobs)}")
    print(f"Analyzed: {len(selected)}")
    print()
    print(render_quality_report(selected))

    if args.samples_output:
        samples = [
            {
                "source": job.source,
                "company": job.company,
                "title": job.title,
                "id": job.id,
                "description_status": job.description_status,
                "description_length": job.description_length,
                "description": job.description,
                "required_skills": job.required_skills,
                "preferred_skills": job.preferred_skills,
                "skills_status": job.skills_status,
                "experience_required": job.experience_required,
                "experience_years_required": job.experience_years_required,
                "experience_status": job.experience_status,
            }
            for job in selected
        ]
        with open(args.samples_output, "w", encoding="utf-8") as output_file:
            json.dump(samples, output_file, indent=2, ensure_ascii=False)
        print(f"Samples written: {args.samples_output}")


if __name__ == "__main__":
    main()