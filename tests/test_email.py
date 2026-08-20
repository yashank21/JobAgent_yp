"""
Simple email test for JobAgent.

Sends a fake JobMatch to verify that the email
configuration and SMTP connection work.
"""

from app.email.email_service import EmailService
from app.models.job import Job
from app.models.match import JobMatch


def main():
    job = Job(
        id="test-job-1",
        title="Software Engineer - JobAgent Test",
        company="JobAgent Test Company",
        location="Bangalore, India",
        application_url="https://example.com",
    )

    match = JobMatch(
        job=job,
        eligible=True,
        skill_score=85.0,
        role_score=90.0,
        experience_score=80.0,
        location_score=100.0,
        final_score=88.5,
        eligibility_reasons=[],
    )

    email_service = EmailService()

    email_service.send_job_digest(
        [match],
    )

    print("TEST EMAIL SENT SUCCESSFULLY")


if __name__ == "__main__":
    main()