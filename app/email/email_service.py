"""
Email service for JobAgent.

Responsible only for formatting and sending job-match emails.
It does not perform collection, eligibility, freshness, or scoring.
"""

import html as html_lib
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

    @staticmethod
    def _esc(text: str) -> str:
        """Escape text for safe HTML embedding."""
        return html_lib.escape(str(text))

    @staticmethod
    def _score_color(score: float) -> str:
        """Return a hex color based on score value."""
        if score >= 80:
            return "#16a34a"
        if score >= 60:
            return "#ca8a04"
        return "#dc2626"

    @staticmethod
    def _score_bg(score: float) -> str:
        """Return a light background color for score pills."""
        if score >= 80:
            return "#dcfce7"
        if score >= 60:
            return "#fef9c3"
        return "#fee2e2"

    def _build_html(
        self,
        matches: list[JobMatch],
    ) -> str:
        """Build HTML email body."""

        if not matches:
            return """
            <html>
            <head>
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin:0;padding:0;
                         font-family:Arial,Helvetica,sans-serif;
                         background-color:#f4f5f7;">
                <table width="100%" cellpadding="0"
                       cellspacing="0"
                       style="background-color:#f4f5f7;
                              padding:32px 0;">
                <tr><td align="center">
                <table width="600" cellpadding="0"
                       cellspacing="0"
                       style="background:#fff;
                              border-radius:12px;
                              overflow:hidden;
                              box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                <tr><td style="background:#111827;padding:32px 40px;">
                    <h1 style="margin:0;color:#fff;font-size:22px;
                               font-weight:700;letter-spacing:-0.3px;">
                      JobAgent</h1>
                    <p style="margin:6px 0 0;color:#9ca3af;
                              font-size:13px;">
                      No matching jobs found</p>
                </td></tr>
                <tr><td style="padding:40px;text-align:center;
                              color:#6b7280;font-size:14px;">
                    No eligible jobs were found in the latest run.
                </td></tr>
                </table>
                </td></tr></table>
            </body>
            </html>
            """

        summary_color = (
            "#16a34a" if len(matches) >= 5
            else "#2563eb"
        )

        jobs_html = ""

        for index, match in enumerate(matches, start=1):
            job = match.job
            esc = self._esc

            posted = (
                job.posted_at.strftime("%d %b %Y, %H:%M UTC")
                if job.posted_at
                else "Unknown"
            )

            location_display = esc(
                job.location or "Not specified"
            )

            if job.remote_type:
                location_display += f" ({esc(job.remote_type)})"

            apply_section = ""
            if job.application_url:
                apply_section = f"""
                <a href="{esc(job.application_url)}"
                   style="
                     display:inline-block;
                     background:#2563eb;
                     color:#ffffff;
                     text-decoration:none;
                     font-size:13px;
                     font-weight:600;
                     padding:10px 24px;
                     border-radius:6px;
                     margin-top:16px;
                   ">Apply Now &rarr;</a>
                """

            explanation_items = ""
            for exp in match.eligibility_reasons:
                explanation_items += (
                    f'<li style="padding:3px 0;font-size:13px;'
                    f'color:#374151;">{esc(exp)}</li>\n'
                )

            if not explanation_items:
                explanation_items = (
                    '<li style="padding:3px 0;font-size:13px;'
                    'color:#6b7280;">No eligibility details</li>'
                )

            score_block = self._build_score_section(match)

            jobs_html += f"""
            <div style="
                background:#ffffff;
                border:1px solid #e5e7eb;
                border-radius:10px;
                margin-bottom:20px;
                overflow:hidden;
            ">
              <table width="100%" cellpadding="0"
                     cellspacing="0">
              <tr>
                <td style="padding:24px 28px 20px;">
                  <table width="100%" cellpadding="0"
                         cellspacing="0">
                  <tr>
                    <td style="vertical-align:top;">
                      <p style="margin:0 0 4px;font-size:12px;
                                font-weight:600;color:#9ca3af;
                                text-transform:uppercase;
                                letter-spacing:0.5px;">
                        #{esc(str(index))}</p>
                      <h2 style="margin:0 0 4px;font-size:18px;
                                 font-weight:700;color:#111827;
                                 line-height:1.3;">
                        {esc(job.title)}</h2>
                      <p style="margin:0;font-size:14px;
                                color:#4b5563;font-weight:500;">
                        {esc(job.company)}</p>
                    </td>
                    <td style="vertical-align:top;text-align:right;
                               width:110px;">
                      {score_block}
                    </td>
                  </tr>
                  </table>

                  <table width="100%" cellpadding="0"
                         cellspacing="0"
                         style="margin-top:16px;">
                  <tr>
                    <td style="font-size:13px;color:#6b7280;
                               padding-right:20px;">
                      <strong style="color:#374151;">
                        Location:</strong>
                      {location_display}
                    </td>
                    <td style="font-size:13px;color:#6b7280;">
                      <strong style="color:#374151;">
                        Posted:</strong> {posted}
                    </td>
                  </tr>
                  </table>

                  <div style="margin-top:18px;padding-top:16px;
                              border-top:1px solid #f3f4f6;">
                    <p style="margin:0 0 8px;font-size:13px;
                              font-weight:600;color:#374151;">
                      Match Details</p>
                    <table width="100%" cellpadding="0"
                           cellspacing="0"
                           style="margin-bottom:12px;">
                    <tr>
                      {self._score_pill("Role", match.role_score)}
                      {self._score_pill("Skills", match.skill_score)}
                      {self._score_pill("Experience", match.experience_score)}
                      {self._score_pill("Location", match.location_score)}
                    </tr>
                    </table>

                    <p style="margin:0 0 6px;font-size:13px;
                              font-weight:600;color:#374151;">
                      Key Explanations</p>
                    <ul style="margin:0;padding-left:18px;
                               list-style:none;">
                      {explanation_items}
                    </ul>
                  </div>

                  <div style="margin-top:16px;text-align:center;">
                    {apply_section}
                  </div>

                </td>
              </tr>
              </table>
            </div>
            """

        return f"""
        <html>
        <head>
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0;padding:0;
                     font-family:Arial,Helvetica,sans-serif;
                     background-color:#f4f5f7;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background-color:#f4f5f7;
                      padding:32px 0;">
        <tr><td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;
                      background:#ffffff;
                      border-radius:12px;
                      overflow:hidden;
                      box-shadow:0 1px 3px rgba(0,0,0,0.08);">

          <tr>
            <td style="background:#111827;padding:28px 36px;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;
                         font-weight:700;letter-spacing:-0.3px;">
                JobAgent</h1>
              <p style="margin:6px 0 0;color:#9ca3af;
                        font-size:13px;">
                {len(matches)} matching
                {"job" if len(matches) == 1 else "jobs"} found
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding:28px 36px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:{summary_color};
                           border-radius:8px;padding:14px 20px;
                           color:#ffffff;">
                  <span style="font-size:28px;font-weight:700;">
                    {len(matches)}</span>
                  <span style="font-size:13px;margin-left:8px;
                               opacity:0.9;">
                    eligible{"s" if len(matches) != 1 else ""}
                    {"job" if len(matches) == 1 else "jobs"}
                    ranked by match score</span>
                </td>
              </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:12px 36px 32px;">
              {jobs_html}
            </td>
          </tr>

          <tr>
            <td style="padding:20px 36px;
                        border-top:1px solid #e5e7eb;
                        background:#f9fafb;
                        text-align:center;">
              <p style="margin:0;font-size:12px;color:#9ca3af;">
                Generated automatically by
                <strong>JobAgent</strong></p>
            </td>
          </tr>

        </table>
        </td></tr>
        </table>
        </body>
        </html>
        """

    def _build_score_section(self, match: JobMatch) -> str:
        """Build the circular score badge for a job card."""
        color = self._score_color(match.final_score)
        return f"""
        <div style="
            display:inline-block;
            text-align:center;
        ">
          <div style="
            width:64px;height:64px;
            border-radius:50%;
            border:3px solid {color};
            line-height:58px;
            font-size:20px;font-weight:700;
            color:{color};
            margin:0 auto;
          ">{match.final_score:.1f}</div>
          <p style="margin:4px 0 0;font-size:11px;
                    color:#6b7280;font-weight:600;">
            MATCH</p>
        </div>
        """

    def _score_pill(self, label: str, score: float) -> str:
        """Build a single score pill cell for the detail row."""
        color = self._score_color(score)
        bg = self._score_bg(score)
        return f"""
        <td style="padding:4px 6px 4px 0;">
          <span style="
            display:inline-block;
            background:{bg};
            color:{color};
            font-size:12px;
            font-weight:600;
            padding:4px 10px;
            border-radius:12px;
          ">{self._esc(label)} {score:.1f}</span>
        </td>
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
