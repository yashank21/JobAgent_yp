import asyncio

from app.collectors.wellfound import WellfoundCollector
from app.storage.job_storage import save_jobs


async def main():
    collector = WellfoundCollector()

    jobs = await collector.collect_async()

    save_jobs(jobs)

    print(
        f"Saved {len(jobs)} jobs to "
        f"data/wellfound_jobs.json"
    )


if __name__ == "__main__":
    asyncio.run(main())