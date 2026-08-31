from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.collectors.wellfound import WellfoundCollector, _wellfound_role_slug


class FakeHTTPClient:

    def __init__(self, response):
        self.response = response
        self.requested_url = None

    def get(self, url):
        self.requested_url = url
        return self.response


def test_parse_wellfound_job():

    fake_http = FakeHTTPClient({})

    collector = WellfoundCollector(
        http_client=fake_http,
    )

    raw_job = {
        "id": 123,
        "title": "AI Engineer",
        "company": "Example AI",
        "location": "Bengaluru, India",
        "remote_type": "Hybrid",
        "experience_required": "1-3 years",
        "experience_years_required": 1.0,
        "required_skills_text": (
            "Python, SQL, PyTorch"
        ),
        "preferred_skills_text": (
            "Docker, AWS"
        ),
        "salary_min_lpa": 8.0,
        "salary_max_lpa": 14.0,
        "description": (
            "<p>Build AI systems using "
            "Python and PyTorch.</p>"
        ),
        "application_url": (
            "https://example.com/jobs/123"
        ),
        "source_url": (
            "https://example.com/jobs/123"
        ),
        "posted_at": (
            "2026-08-17T08:00:00+00:00"
        ),
    }

    job = collector._parse_job(raw_job)

    assert job.id == "123"
    assert job.title == "AI Engineer"
    assert job.company == "Example AI"

    assert job.location == "Bengaluru, India"
    assert job.remote_type == "Hybrid"

    assert job.experience_required == "1-3 years"
    assert job.experience_years_required == 1.0

    assert "python" in job.required_skills
    assert "sql" in job.required_skills
    assert "pytorch" in job.required_skills

    assert "docker" in job.preferred_skills
    assert "aws" in job.preferred_skills

    assert job.salary_min_lpa == 8.0
    assert job.salary_max_lpa == 14.0

    assert job.description == (
        "Build AI systems using "
        "Python and PyTorch."
    )

    assert job.application_url == (
        "https://example.com/jobs/123"
    )

    assert job.source == "wellfound"

    assert job.posted_at == datetime.fromisoformat(
        "2026-08-17T08:00:00+00:00"
    )


def test_parse_wellfound_job_uses_enrichment_when_experience_is_none():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    job = collector._parse_job({
        "id": 456,
        "title": "AI Engineer",
        "company": "Example AI",
        "description": "3+ years of experience with Python.",
        "experience_years_required": None,
    })

    assert job.experience_years_required == 3.0


def test_parse_wellfound_job_preserves_explicit_experience_value():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    job = collector._parse_job({
        "id": 789,
        "title": "AI Engineer",
        "company": "Example AI",
        "description": "3+ years of experience with Python.",
        "experience_years_required": 2.0,
    })

    assert job.experience_years_required == 2.0


def test_wellfound_urls_follow_user_roles_not_a_hardcoded_ai_path():
    from app.collectors.wellfound import wellfound_search_urls

    urls = wellfound_search_urls(
        roles=["Backend Engineer", "Software Engineer"],
        locations=["India"],
    )

    assert urls == [
        "https://wellfound.com/role/l/backend-engineer/india",
        "https://wellfound.com/role/l/software-engineer/india",
    ]
    assert all("ai-engineer" not in url for url in urls)


# ---------------------------------------------------------
# _extract_link_job_id
# ---------------------------------------------------------


def _make_link(href: str):
    link = MagicMock()
    link.get_attribute = AsyncMock(return_value=href)
    link.inner_text = AsyncMock(return_value="")
    return link


def _make_link_with_text(text: str, href: str):
    link = MagicMock()
    link.get_attribute = AsyncMock(return_value=href)
    link.inner_text = AsyncMock(return_value=text)
    return link


def test_extract_link_job_id_numeric():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))
    link = _make_link("/jobs/12345")

    job_id = asyncio.run(
        collector._extract_link_job_id(link)
    )

    assert job_id == "12345"


def test_extract_link_job_id_fallback_hash():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))
    link = _make_link("/jobs/some-slug-no-number")

    job_id = asyncio.run(
        collector._extract_link_job_id(link)
    )

    assert job_id.startswith("wf-")


def test_extract_link_job_id_returns_empty_for_non_jobs():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))
    link = _make_link("/companies/example")

    job_id = asyncio.run(
        collector._extract_link_job_id(link)
    )

    assert job_id == ""


# ---------------------------------------------------------
# Cross-URL deduplication in _fetch_url_jobs
# ---------------------------------------------------------


import asyncio


def _make_page(links_on_page):
    """
    Build a mock Playwright page that:
    - Returns no pagination links (single page)
    - Returns the given link elements
    """
    page = AsyncMock()
    page.url = "https://wellfound.com/role/l/test/india"

    async def query_selector_all(selector):
        if selector == "a":
            return []
        return links_on_page

    page.query_selector_all = AsyncMock(
        side_effect=query_selector_all
    )

    page.set_extra_http_headers = AsyncMock()
    page.goto = AsyncMock(return_value=MagicMock(status=200))
    page.wait_for_timeout = AsyncMock()
    page.wait_for_selector = AsyncMock()

    return page


def _make_page_multi(pagination_links, job_links_per_page):
    """
    Build a mock Playwright page for multi-page pagination tests.

    pagination_links:   mock <a> elements returned for selector "a"
    job_links_per_page: list of lists — each inner list is the job
                        links returned for that page's
                        query_selector_all("a[href*='/jobs/']") call
    """
    page = AsyncMock()
    page.url = "https://wellfound.com/role/l/test/india"
    call_index = [0]

    async def query_selector_all(selector):
        if selector == "a":
            return pagination_links
        idx = call_index[0]
        call_index[0] += 1
        if idx < len(job_links_per_page):
            return job_links_per_page[idx]
        return []

    page.query_selector_all = AsyncMock(
        side_effect=query_selector_all
    )

    page.set_extra_http_headers = AsyncMock()
    page.goto = AsyncMock(return_value=MagicMock(status=200))
    page.wait_for_timeout = AsyncMock()
    page.wait_for_selector = AsyncMock()

    return page


def test_cross_url_dedup_skips_detail_page_for_seen_id():
    """
    When cross_url_seen_ids contains a job ID, _extract_job_from_link
    must NOT be called for that job — the expensive detail page
    visit is skipped entirely.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    # Link that would yield job_id "111"
    link_a = _make_link("/jobs/111")
    # Link that would yield job_id "222"
    link_b = _make_link("/jobs/222")

    page = _make_page([link_a, link_b])

    detail_page = AsyncMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=detail_page)

    cross_seen = {"111"}  # Job 111 already seen from a prior URL

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        mock_extract.return_value = {
            "id": "222",
            "title": "Engineer",
            "company": "Co",
            "location": "",
            "remote_type": "",
            "experience_required": "",
            "experience_years_required": None,
            "required_skills_text": "",
            "preferred_skills_text": "",
            "salary_min_lpa": None,
            "salary_max_lpa": None,
            "description": "",
            "application_url": "https://wellfound.com/jobs/222",
            "source_url": "https://wellfound.com/jobs/222",
            "posted_at": None,
        }

        raw_jobs = asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
                cross_url_seen_ids=cross_seen,
            )
        )

    # _extract_job_from_link should only be called once (for job 222),
    # NOT for job 111 which was already in cross_url_seen_ids.
    assert mock_extract.call_count == 1

    # Only job 222 should be returned
    assert len(raw_jobs) == 1
    assert raw_jobs[0]["id"] == "222"


def test_cross_url_dedup_allows_new_jobs():
    """
    Jobs whose IDs are NOT in cross_url_seen_ids are extracted normally.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    link_a = _make_link("/jobs/333")
    link_b = _make_link("/jobs/444")

    page = _make_page([link_a, link_b])

    detail_page = AsyncMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=detail_page)

    cross_seen = set()  # Nothing seen yet

    ref_time = datetime.now(timezone.utc)

    fake_raw = {
        "id": "placeholder",
        "title": "Engineer",
        "company": "Co",
        "location": "",
        "remote_type": "",
        "experience_required": "",
        "experience_years_required": None,
        "required_skills_text": "",
        "preferred_skills_text": "",
        "salary_min_lpa": None,
        "salary_max_lpa": None,
        "description": "",
        "application_url": "",
        "source_url": "",
        "posted_at": None,
    }

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        call_count = 0

        async def fake_extract(page, link, ref_time):
            nonlocal call_count
            call_count += 1
            return {**fake_raw, "id": str(call_count)}

        mock_extract.side_effect = fake_extract

        raw_jobs = asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
                cross_url_seen_ids=cross_seen,
            )
        )

    # Both new jobs should be extracted
    assert mock_extract.call_count == 2
    assert len(raw_jobs) == 2


def test_cross_url_dedup_none_skips_check():
    """
    When cross_url_seen_ids is None (default), the cross-URL check
    is skipped entirely — backward compatible behavior.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    link_a = _make_link("/jobs/555")

    page = _make_page([link_a])

    detail_page = AsyncMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=detail_page)

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        mock_extract.return_value = {
            "id": "555",
            "title": "Engineer",
            "company": "Co",
            "location": "",
            "remote_type": "",
            "experience_required": "",
            "experience_years_required": None,
            "required_skills_text": "",
            "preferred_skills_text": "",
            "salary_min_lpa": None,
            "salary_max_lpa": None,
            "description": "",
            "application_url": "https://wellfound.com/jobs/555",
            "source_url": "https://wellfound.com/jobs/555",
            "posted_at": None,
        }

        # cross_url_seen_ids=None (default) means no cross-URL check
        raw_jobs = asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
            )
        )

    # Job is extracted normally even if its ID would be in a set
    assert mock_extract.call_count == 1
    assert len(raw_jobs) == 1


def test_cross_url_dedup_same_id_different_urls():
    """
    The same job (same numeric ID) found by two different role search
    URLs is only extracted once — the detail page is visited only
    for the first URL.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    # Simulate: first URL returns job 111, second URL also has job 111
    link_first = _make_link("/jobs/111")
    link_second = _make_link("/jobs/111")

    page_first = _make_page([link_first])
    page_second = _make_page([link_second])

    detail_page = AsyncMock()

    ref_time = datetime.now(timezone.utc)

    # --- First URL: job 111 is extracted normally ---
    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        mock_extract.return_value = {
            "id": "111",
            "title": "AI Engineer",
            "company": "Acme",
            "location": "India",
            "remote_type": "",
            "experience_required": "",
            "experience_years_required": None,
            "required_skills_text": "",
            "preferred_skills_text": "",
            "salary_min_lpa": None,
            "salary_max_lpa": None,
            "description": "",
            "application_url": "https://wellfound.com/jobs/111",
            "source_url": "https://wellfound.com/jobs/111",
            "posted_at": None,
        }

        raw_jobs_1 = asyncio.run(
            collector._fetch_url_jobs(
                page_first,
                "https://wellfound.com/role/l/ai-engineer/india",
                ref_time,
                cross_url_seen_ids=set(),
            )
        )

        assert mock_extract.call_count == 1
        assert len(raw_jobs_1) == 1

    # --- Second URL: job 111 is skipped (already in cross_seen) ---
    cross_seen = {"111"}

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        raw_jobs_2 = asyncio.run(
            collector._fetch_url_jobs(
                page_second,
                "https://wellfound.com/role/l/software-engineer/india",
                ref_time,
                cross_url_seen_ids=cross_seen,
            )
        )

        # _extract_job_from_link should NOT be called — the detail
        # page visit is skipped entirely for the duplicate.
        assert mock_extract.call_count == 0
        assert len(raw_jobs_2) == 0


# ---------------------------------------------------------
# Pagination early termination
# ---------------------------------------------------------


_FAKE_RAW_JOB = {
    "id": "placeholder",
    "title": "Engineer",
    "company": "Co",
    "location": "",
    "remote_type": "",
    "experience_required": "",
    "experience_years_required": None,
    "required_skills_text": "",
    "preferred_skills_text": "",
    "salary_min_lpa": None,
    "salary_max_lpa": None,
    "description": "",
    "application_url": "",
    "source_url": "",
    "posted_at": None,
}


def test_pagination_early_stop_on_duplicate_page():
    """
    When page 2 returns only job links already seen on page 1,
    pagination stops early and only page-1 jobs are extracted.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    pag_1 = _make_link_with_text(
        "1", "/role/l/test/india?page=1"
    )
    pag_2 = _make_link_with_text(
        "2", "/role/l/test/india?page=2"
    )

    link_a = _make_link("/jobs/100")
    link_b = _make_link("/jobs/200")

    page = _make_page_multi(
        pagination_links=[pag_1, pag_2],
        job_links_per_page=[
            [link_a, link_b],
            [_make_link("/jobs/100"), _make_link("/jobs/200")],
        ],
    )

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        call_count = 0

        async def fake_extract(page, link, ref_time):
            nonlocal call_count
            call_count += 1
            href = await link.get_attribute("href")
            return {
                **_FAKE_RAW_JOB,
                "id": str(call_count),
                "application_url": f"https://wellfound.com{href}",
                "source_url": f"https://wellfound.com{href}",
            }

        mock_extract.side_effect = fake_extract

        raw_jobs = asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
            )
        )

    assert mock_extract.call_count == 2
    assert len(raw_jobs) == 2
    assert raw_jobs[0]["id"] == "1"
    assert raw_jobs[1]["id"] == "2"


def test_pagination_all_pages_visited_when_each_has_new_jobs():
    """
    When each page contains at least one genuinely new job link,
    all pages are processed — no early termination.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    pag_1 = _make_link_with_text(
        "1", "/role/l/test/india?page=1"
    )
    pag_2 = _make_link_with_text(
        "2", "/role/l/test/india?page=2"
    )
    pag_3 = _make_link_with_text(
        "3", "/role/l/test/india?page=3"
    )

    page = _make_page_multi(
        pagination_links=[pag_1, pag_2, pag_3],
        job_links_per_page=[
            [_make_link("/jobs/100")],
            [_make_link("/jobs/200")],
            [_make_link("/jobs/300")],
        ],
    )

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        call_count = 0

        async def fake_extract(page, link, ref_time):
            nonlocal call_count
            call_count += 1
            href = await link.get_attribute("href")
            return {
                **_FAKE_RAW_JOB,
                "id": str(call_count),
                "application_url": f"https://wellfound.com{href}",
                "source_url": f"https://wellfound.com{href}",
            }

        mock_extract.side_effect = fake_extract

        raw_jobs = asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
            )
        )

    assert mock_extract.call_count == 3
    assert len(raw_jobs) == 3
    assert raw_jobs[0]["id"] == "1"
    assert raw_jobs[1]["id"] == "2"
    assert raw_jobs[2]["id"] == "3"


# ---------------------------------------------------------
# DOM-aware wait tests
# ---------------------------------------------------------


def test_dom_aware_wait_invoked_for_page_gt_1():
    """
    For page > 1, _fetch_url_jobs calls wait_for_selector
    with the correct selector and timeout before querying links.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    pag_1 = _make_link_with_text(
        "1", "/role/l/test/india?page=1"
    )
    pag_2 = _make_link_with_text(
        "2", "/role/l/test/india?page=2"
    )

    link_p1 = _make_link("/jobs/100")
    link_p2 = _make_link("/jobs/200")

    page = _make_page_multi(
        pagination_links=[pag_1, pag_2],
        job_links_per_page=[[link_p1], [link_p2]],
    )

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:

        async def fake_extract(page, link, ref_time):
            href = await link.get_attribute("href")
            return {
                **_FAKE_RAW_JOB,
                "id": href,
                "application_url": (
                    f"https://wellfound.com{href}"
                ),
                "source_url": (
                    f"https://wellfound.com{href}"
                ),
            }

        mock_extract.side_effect = fake_extract

        asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
            )
        )

    # wait_for_selector called once (for page 2 only)
    page.wait_for_selector.assert_called_once()

    call_args = page.wait_for_selector.call_args
    assert call_args[0][0] == "a[href*='/jobs/']"
    assert call_args[1]["timeout"] == 10000


def test_page_1_skips_navigation_and_wait():
    """
    For page 1, _fetch_url_jobs does NOT call wait_for_selector.
    The page is already loaded from the initial navigation.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    link = _make_link("/jobs/100")

    page = _make_page([link])

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:

        async def fake_extract(page, link, ref_time):
            href = await link.get_attribute("href")
            return {
                **_FAKE_RAW_JOB,
                "id": href,
                "application_url": (
                    f"https://wellfound.com{href}"
                ),
                "source_url": (
                    f"https://wellfound.com{href}"
                ),
            }

        mock_extract.side_effect = fake_extract

        asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/test/india",
                ref_time,
            )
        )

    # Page 1 should NOT trigger wait_for_selector
    page.wait_for_selector.assert_not_called()


# ---------------------------------------------------------
# Wellfound role slug mapping
# ---------------------------------------------------------


def test_wellfound_role_slug_ai_ml_engineer():
    """'ai/ml engineer' must map to 'ai-engineer', NOT 'ai-ml-engineer'."""
    assert _wellfound_role_slug("ai/ml engineer") == "ai-engineer"


def test_wellfound_role_slug_ai_ml_engineer_url():
    """URL generated for 'ai/ml engineer' must contain /role/l/ai-engineer/."""
    from app.collectors.wellfound import wellfound_search_urls

    urls = wellfound_search_urls(
        roles=["ai/ml engineer"],
        locations=["India"],
    )
    assert urls == [
        "https://wellfound.com/role/l/ai-engineer/india"
    ]


def test_wellfound_role_slug_ai_ml_no_longer_generates_ai_ml_engineer():
    """The old invalid slug 'ai-ml-engineer' must NOT appear in any URL."""
    from app.collectors.wellfound import wellfound_search_urls

    urls = wellfound_search_urls(
        roles=["ai/ml engineer"],
        locations=["India"],
    )
    assert not any("ai-ml-engineer" in url for url in urls)


def test_wellfound_role_slug_ai_ml_space():
    """'ai ml engineer' (space separated) maps to 'ai-engineer'."""
    assert _wellfound_role_slug("ai ml engineer") == "ai-engineer"


def test_wellfound_role_slug_ai_engineer():
    """'ai engineer' maps to 'ai-engineer'."""
    assert _wellfound_role_slug("ai engineer") == "ai-engineer"


def test_wellfound_role_slug_machine_learning_engineer():
    """'machine learning engineer' maps to 'machine-learning-engineer'."""
    assert _wellfound_role_slug("machine learning engineer") == "machine-learning-engineer"


def test_wellfound_role_slug_ml_engineer():
    """'ml engineer' maps to 'machine-learning-engineer'."""
    assert _wellfound_role_slug("ml engineer") == "machine-learning-engineer"


def test_wellfound_role_slug_mle():
    """'mle' maps to 'machine-learning-engineer'."""
    assert _wellfound_role_slug("mle") == "machine-learning-engineer"


def test_wellfound_role_slug_software_engineer():
    """'software engineer' maps to 'software-engineer'."""
    assert _wellfound_role_slug("software engineer") == "software-engineer"


def test_wellfound_role_slug_backend_engineer():
    """'backend engineer' maps to 'backend-engineer'."""
    assert _wellfound_role_slug("backend engineer") == "backend-engineer"


def test_wellfound_role_slug_unknown_role_returns_none():
    """Unknown roles must return None — no guessing."""
    assert _wellfound_role_slug("quantum computing researcher") is None


def test_wellfound_role_slug_case_insensitive():
    """Mapping is case-insensitive."""
    assert _wellfound_role_slug("AI Engineer") == "ai-engineer"
    assert _wellfound_role_slug("AI/ML Engineer") == "ai-engineer"
    assert _wellfound_role_slug("ML Engineer") == "machine-learning-engineer"


def test_wellfound_search_urls_skips_unknown_roles():
    """Unknown roles are silently skipped; known roles still produce URLs."""
    from app.collectors.wellfound import wellfound_search_urls

    urls = wellfound_search_urls(
        roles=["quantum researcher", "ai/ml engineer"],
        locations=["India"],
    )
    assert urls == [
        "https://wellfound.com/role/l/ai-engineer/india"
    ]


def test_wellfound_search_urls_deduplicates_slugs():
    """Different role strings that map to the same slug produce one URL."""
    from app.collectors.wellfound import wellfound_search_urls

    urls = wellfound_search_urls(
        roles=["ai engineer", "ai/ml engineer", "ai ml engineer"],
        locations=["India"],
    )
    assert urls == [
        "https://wellfound.com/role/l/ai-engineer/india"
    ]


# ---------------------------------------------------------
# Redirect detection guard
# ---------------------------------------------------------


def test_redirect_to_location_page_returns_empty():
    """
    When a role URL redirects to /location/india, _fetch_url_jobs
    returns an empty list instead of silently collecting generic results.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    page = AsyncMock()
    page.set_extra_http_headers = AsyncMock()
    page.url = "https://wellfound.com/location/india"

    # Simulate: goto resolves to /location/india instead of /role/l/...
    response_mock = MagicMock()
    response_mock.status = 200

    async def fake_goto(url, **kwargs):
        page.url = "https://wellfound.com/location/india"
        return response_mock

    page.goto = AsyncMock(side_effect=fake_goto)
    page.wait_for_timeout = AsyncMock()

    ref_time = datetime.now(timezone.utc)

    raw_jobs = asyncio.run(
        collector._fetch_url_jobs(
            page,
            "https://wellfound.com/role/l/ai-ml-engineer/india",
            ref_time,
        )
    )

    assert raw_jobs == []


def test_valid_role_url_proceeds_normally():
    """
    When the resolved URL stays on a role page, _fetch_url_jobs
    proceeds with normal extraction.
    """
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    link = _make_link("/jobs/100")

    page = AsyncMock()
    page.set_extra_http_headers = AsyncMock()
    page.url = "https://wellfound.com/role/l/ai-engineer/india"

    # Simulate: goto resolves to a valid role page
    response_mock = MagicMock()
    response_mock.status = 200

    async def fake_goto(url, **kwargs):
        page.url = "https://wellfound.com/role/l/ai-engineer/india"
        return response_mock

    page.goto = AsyncMock(side_effect=fake_goto)
    page.wait_for_timeout = AsyncMock()

    async def query_selector_all(selector):
        if selector == "a":
            return []
        return [link]

    page.query_selector_all = AsyncMock(
        side_effect=query_selector_all
    )

    detail_page = AsyncMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=detail_page)

    ref_time = datetime.now(timezone.utc)

    with patch.object(
        collector,
        "_extract_job_from_link",
        new_callable=AsyncMock,
    ) as mock_extract:
        mock_extract.return_value = {
            "id": "100",
            "title": "AI Engineer",
            "company": "Co",
            "location": "",
            "remote_type": "",
            "experience_required": "",
            "experience_years_required": None,
            "required_skills_text": "",
            "preferred_skills_text": "",
            "salary_min_lpa": None,
            "salary_max_lpa": None,
            "description": "",
            "application_url": "https://wellfound.com/jobs/100",
            "source_url": "https://wellfound.com/jobs/100",
            "posted_at": None,
        }

        raw_jobs = asyncio.run(
            collector._fetch_url_jobs(
                page,
                "https://wellfound.com/role/l/ai-engineer/india",
                ref_time,
            )
        )

    assert len(raw_jobs) == 1
    assert raw_jobs[0]["id"] == "100"