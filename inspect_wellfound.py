import json
import re
from pathlib import Path


HTML_FILE = Path("wellfound_debug.html")


def load_apollo_data():
    html = HTML_FILE.read_text(encoding="utf-8")

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )

    if not match:
        raise RuntimeError("__NEXT_DATA__ not found")

    data = json.loads(match.group(1))

    return (
        data["props"]
        ["pageProps"]
        ["apolloState"]
        ["data"]
    )


def build_job_company_mapping(apollo_data):

    jobs = {
        key.split(":", 1)[1]: value
        for key, value in apollo_data.items()
        if key.startswith("JobListingSearchResult:")
    }

    startups = [
        value
        for value in apollo_data.values()
        if (
            isinstance(value, dict)
            and value.get("__typename") == "StartupResult"
        )
    ]

    job_to_company = {}

    for startup in startups:

        company_name = startup.get("name", "")

        for reference in startup.get(
            "highlightedJobListings",
            [],
        ):

            ref = reference.get("__ref", "")

            if not ref.startswith(
                "JobListingSearchResult:"
            ):
                continue

            job_id = ref.split(":", 1)[1]

            job_to_company[job_id] = {
                "company": company_name,
                "startup_id": startup.get("id", ""),
                "startup_slug": startup.get("slug", ""),
                "is_yc": any(
                    "YC-" in badge.get("__ref", "")
                    for badge in startup.get("badges", [])
                ),
            }

    return jobs, job_to_company


def main():

    apollo_data = load_apollo_data()

    jobs, job_to_company = (
        build_job_company_mapping(apollo_data)
    )

    print("=" * 80)
    print("WELLFOUND JOB -> COMPANY MAPPING")
    print("=" * 80)

    print(f"Jobs found: {len(jobs)}")
    print(
        f"Jobs with company mapping: "
        f"{len(job_to_company)}"
    )

    print()

    for job_id, job in jobs.items():

        company_data = job_to_company.get(job_id)

        if company_data:

            yc = "YES" if company_data["is_yc"] else "NO"

            print(
                f"{job_id:<10} | "
                f"{company_data['company']:<30} | "
                f"YC: {yc:<3} | "
                f"{job.get('title', '')}"
            )

        else:

            print(
                f"{job_id:<10} | "
                f"{'UNKNOWN':<30} | "
                f"YC: ?   | "
                f"{job.get('title', '')}"
            )


if __name__ == "__main__":
    main()