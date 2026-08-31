"""
Tests for the JobAgent email HTML digest.
"""

from datetime import datetime, timezone

from app.email.email_service import EmailService
from app.models.job import Job
from app.models.match import JobMatch


def _make_match(**overrides) -> JobMatch:
    job = overrides.pop("job", None)
    if job is None:
        job = Job(
            id="job-1",
            title="Software Engineer",
            company="Acme Corp",
            location="Bangalore, India",
            application_url="https://example.com/apply",
            posted_at=datetime(
                2025, 6, 15, 10, 0,
                tzinfo=timezone.utc,
            ),
        )
    defaults = dict(
        job=job,
        eligible=True,
        skill_score=85.0,
        role_score=90.0,
        experience_score=80.0,
        location_score=100.0,
        final_score=88.5,
        eligibility_reasons=[
            "Python — required skill match",
        ],
    )
    defaults.update(overrides)
    return JobMatch(**defaults)


def _build(matches):
    svc = EmailService.__new__(EmailService)
    return svc._build_html(matches)


class TestEmptyDigest:
    def test_empty_matches_returns_html(self):
        html = _build([])
        assert "<html>" in html
        assert "No matching jobs" in html

    def test_empty_matches_is_valid_structure(self):
        html = _build([])
        assert "</html>" in html
        assert "</body>" in html


class TestSingleJob:
    def test_contains_job_title(self):
        match = _make_match()
        html = _build([match])
        assert "Software Engineer" in html

    def test_contains_company(self):
        match = _make_match()
        html = _build([match])
        assert "Acme Corp" in html

    def test_contains_final_score(self):
        match = _make_match(final_score=88.5)
        html = _build([match])
        assert "88.5" in html

    def test_contains_role_score(self):
        match = _make_match(role_score=90.0)
        html = _build([match])
        assert "Role" in html
        assert "90.0" in html

    def test_contains_skill_score(self):
        match = _make_match(skill_score=85.0)
        html = _build([match])
        assert "Skills" in html
        assert "85.0" in html

    def test_contains_experience_score(self):
        match = _make_match(experience_score=80.0)
        html = _build([match])
        assert "Experience" in html
        assert "80.0" in html

    def test_contains_location_score(self):
        match = _make_match(location_score=100.0)
        html = _build([match])
        assert "Location" in html
        assert "100.0" in html

    def test_contains_location_text(self):
        match = _make_match()
        html = _build([match])
        assert "Bangalore, India" in html

    def test_contains_apply_button(self):
        match = _make_match()
        html = _build([match])
        assert "https://example.com/apply" in html
        assert "Apply Now" in html

    def test_contains_posted_date(self):
        match = _make_match()
        html = _build([match])
        assert "15 Jun 2025" in html

    def test_contains_eligibility_reasons(self):
        match = _make_match(
            eligibility_reasons=["Python — required skill match"],
        )
        html = _build([match])
        assert "Python — required skill match" in html

    def test_contains_job_counter(self):
        match = _make_match()
        html = _build([match])
        assert "#1" in html

    def test_summary_shows_count(self):
        match = _make_match()
        html = _build([match])
        assert "1 matching" in html
        assert "job found" in html


class TestMultipleJobs:
    def test_all_jobs_rendered(self):
        matches = [
            _make_match(
                job=Job(
                    id=str(i),
                    title=f"Engineer {i}",
                    company=f"Company {i}",
                ),
                final_score=70.0 + i,
            )
            for i in range(5)
        ]
        html = _build(matches)
        for i in range(5):
            assert f"Engineer {i}" in html
            assert f"Company {i}" in html

    def test_summary_shows_plural(self):
        matches = [
            _make_match(
                job=Job(id="1", title="A", company="B"),
            ),
            _make_match(
                job=Job(id="2", title="C", company="D"),
            ),
        ]
        html = _build(matches)
        assert "2 matching" in html
        assert "jobs found" in html

    def test_multiple_job_counters(self):
        matches = [
            _make_match(
                job=Job(id=str(i), title="X", company="Y"),
            )
            for i in range(3)
        ]
        html = _build(matches)
        assert "#1" in html
        assert "#2" in html
        assert "#3" in html


class TestHtmlEscaping:
    def test_script_tag_in_title_is_escaped(self):
        job = Job(
            id="1",
            title='<script>alert("xss")</script>',
            company="Evil Corp",
        )
        match = _make_match(job=job)
        html = _build([match])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_script_tag_in_company_is_escaped(self):
        job = Job(
            id="1",
            title="Engineer",
            company='<img src=x onerror=alert(1)>',
        )
        match = _make_match(job=job)
        html = _build([match])
        assert "<img" not in html
        assert "&lt;img" in html

    def test_angle_brackets_in_location_escaped(self):
        job = Job(
            id="1",
            title="Engineer",
            company="X",
            location="<b>Bold Location</b>",
        )
        match = _make_match(job=job)
        html = _build([match])
        assert "<b>Bold Location</b>" not in html

    def test_ampersand_in_company_escaped(self):
        job = Job(
            id="1",
            title="Engineer",
            company="AT&T Labs",
        )
        match = _make_match(job=job)
        html = _build([match])
        assert "AT&amp;T Labs" in html


class TestNoApplyButton:
    def test_no_apply_button_when_url_missing(self):
        job = Job(
            id="1",
            title="Engineer",
            company="X",
            application_url="",
        )
        match = _make_match(job=job)
        html = _build([match])
        assert "Apply Now" not in html


class TestNoPostedDate:
    def test_unknown_posted_date(self):
        job = Job(
            id="1",
            title="Engineer",
            company="X",
            posted_at=None,
        )
        match = _make_match(job=job)
        html = _build([match])
        assert "Unknown" in html


class TestScoreColors:
    def test_high_score_uses_green(self):
        match = _make_match(final_score=95.0)
        html = _build([match])
        assert "#16a34a" in html

    def test_medium_score_uses_yellow(self):
        match = _make_match(final_score=70.0)
        html = _build([match])
        assert "#ca8a04" in html

    def test_low_score_uses_red(self):
        match = _make_match(final_score=40.0)
        html = _build([match])
        assert "#dc2626" in html


class TestNoEligibilityReasons:
    def test_no_reasons_shows_fallback(self):
        match = _make_match(eligibility_reasons=[])
        html = _build([match])
        assert "No eligibility details" in html
