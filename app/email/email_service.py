"""
Email service for JobAgent.

Responsible only for formatting and sending job-match emails.
It does not perform collection, eligibility, freshness, or scoring.
"""

import os
import smtplib
from email.message import EmailMessage

from app.models.match import JobMatch


class EmailService:
    """Send JobAgent job-match emails."""

    def __init__(self):
        self.smtp_host = os.getenv(
            "EMAIL_SMTP_HOST",
            "smtp.gmail.com",
        )
        self.smtp_port = int(
            os.getenv(
                "EMAIL_SMTP_PORT",
                "465",
            )
        )
        self.sender_email = os.getenv(
            "EMAIL_SENDER",
        )
        self.sender_password = os.getenv(
            "EMAIL_PASSWORD",
        )
        self.recipient_email = os.getenv(
            "EMAIL_RECIPIENT",
        )

        self._validate_config()

    def _validate_config(self):
        """Validate required email configuration."""

        missing = []

        if not self.sender_email:
            missing.append("EMAIL_SENDER")

        if not self.sender_password:
            missing.append("EMAIL_PASSWORD")

        if not self.recipient_email:
            missing.append("EMAIL_RECIPIENT")

        if missing:
            raise ValueError(
                "Missing email configuration: "
                + ", ".join(missing)
            )

    def _build_html(
        self,
        matches: list[JobMatch],
    ) -> str:
        """Build HTML email body."""

        if not matches:
            return """
            <html>
                <body>
                    <h2>JobAgent — No matching jobs</h2>
                    <p>
                        No eligible jobs were found in the
                        latest run.
                    </p>
                </body>
            </html>
            """

        jobs_html = ""

        for index, match in enumerate(matches, start=1):
            job = match.job

            apply_url = job.application_url

            apply_link = ""

            if apply_url:
                apply_link = f"""
                <p>
                    <a href="{apply_url}">
                        Apply / View Job
                    </a>
                </p>
                """

            jobs_html += f"""
            <div style="
                border:1px solid #ddd;
                border-radius:8px;
                padding:16px;
                margin-bottom:16px;
            ">

                <h2>
                    #{index} — {job.company}
                </h2>

                <h3>
                    {job.title}
                </h3>

                <p>
                <strong>Posted:</strong>
                {
                    job.posted_at.strftime("%d %b %Y, %H:%M UTC")
                    if job.posted_at
                    else "Unknown"
                }
                </p>

                <p>
                    <strong>Posted:</strong>
                    {job.posted_at or "Unknown"}
                </p>

                <hr>

                <p>
                    <strong>Final Score:</strong>
                    {match.final_score}
                </p>

                <p>
                    <strong>Role:</strong>
                    {match.role_score}
                    &nbsp; | &nbsp;

                    <strong>Skills:</strong>
                    {match.skill_score}
                    &nbsp; | &nbsp;

                    <strong>Experience:</strong>
                    {match.experience_score}
                    &nbsp; | &nbsp;

                    <strong>Location:</strong>
                    {match.location_score}
                </p>

                {apply_link}

            </div>
            """

        return f"""
        <html>
            <body style="
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: auto;
                padding: 20px;
            ">

                <h1>JobAgent</h1>

                <h2>
                    {len(matches)} new matching jobs
                </h2>

                <p>
                    Jobs collected, filtered and ranked
                    automatically by JobAgent.
                </p>

                {jobs_html}

                <hr>

                <p style="color:#777;">
                    Generated automatically by JobAgent.
                </p>

            </body>
        </html>
        """

    def send_job_digest(
        self,
        matches: list[JobMatch],
    ):
        """Send a job digest email."""

        subject = (
            f"JobAgent — "
            f"{len(matches)} Matching Jobs"
        )

        html_body = self._build_html(matches)

        message = EmailMessage()

        message["From"] = self.sender_email
        message["To"] = self.recipient_email
        message["Subject"] = subject

        message.set_content(
            "JobAgent found "
            f"{len(matches)} matching jobs."
        )

        message.add_alternative(
            html_body,
            subtype="html",
        )

        with smtplib.SMTP_SSL(
            self.smtp_host,
            self.smtp_port,
        ) as smtp:

            smtp.login(
                self.sender_email,
                self.sender_password,
            )

            smtp.send_message(message)
