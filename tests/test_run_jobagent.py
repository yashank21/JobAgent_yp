import sys
from unittest.mock import patch, MagicMock

from app.models.candidate import CandidateProfile
from run_jobagent import (
    apply_default_preferences,
    parse_args,
    main,
)


def _parse(extra_args: list[str]) -> object:
    with patch.object(sys, "argv", ["run_jobagent.py"] + extra_args):
        return parse_args()


def test_parse_args_requires_resume():
    try:
        _parse([])
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass


def test_parse_args_resume_only():
    args = _parse(["--resume", "my_resume.pdf"])
    assert args.resume == "my_resume.pdf"
    assert args.non_interactive is False
    assert args.mode == "refresh"


def test_parse_args_non_interactive_flag():
    args = _parse(
        ["--resume", "r.pdf", "--non-interactive"]
    )
    assert args.resume == "r.pdf"
    assert args.non_interactive is True


def test_apply_default_preferences_does_not_copy_resume_roles():
    profile = CandidateProfile(
        resume_roles=["AI Engineer", "Backend Engineer"],
    )

    result = apply_default_preferences(profile)

    assert result.preferences.preferred_roles == []
    assert result.facts.resume_roles == [
        "AI Engineer",
        "Backend Engineer",
    ]
    assert result is profile


def test_apply_default_preferences_empty_roles():
    profile = CandidateProfile(resume_roles=[])

    result = apply_default_preferences(profile)

    assert result.preferences.preferred_roles == []
    assert result.facts.resume_roles == []
    assert result is profile


def test_apply_default_preferences_does_not_touch_other_fields():
    profile = CandidateProfile(
        resume_roles=["ML Engineer"],
        preferred_locations=["India"],
        minimum_salary_lpa=15.0,
        skills=["Python", "PyTorch"],
    )

    apply_default_preferences(profile)

    assert profile.preferences.preferred_locations == ["India"]
    assert profile.preferences.minimum_salary_lpa == 15.0
    assert profile.facts.skills == ["Python", "PyTorch"]


def test_non_interactive_does_not_call_input(capsys):
    profile = CandidateProfile(
        resume_roles=["SDE", "Software Engineer"],
    )

    result = apply_default_preferences(profile)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.preferences.preferred_roles == []
    assert result.facts.resume_roles == [
        "SDE",
        "Software Engineer",
    ]


# ---------------------------------------------------------
# --mode argument tests
# ---------------------------------------------------------


def test_parse_args_default_mode():
    args = _parse(["--resume", "r.pdf"])
    assert args.mode == "refresh"


def test_parse_args_explicit_refresh_mode():
    args = _parse(["--resume", "r.pdf", "--mode", "refresh"])
    assert args.mode == "refresh"


def test_parse_args_cache_only_mode():
    args = _parse(["--resume", "r.pdf", "--mode", "cache_only"])
    assert args.mode == "cache_only"


def test_parse_args_invalid_mode():
    try:
        _parse(["--resume", "r.pdf", "--mode", "invalid"])
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass


# ---------------------------------------------------------
# main() mode behavior tests (mock-based)
# ---------------------------------------------------------


def test_cache_only_skips_collectors():
    """
    In cache_only mode, no collector classes should be
    instantiated and no network calls should be made.
    """
    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 43,
        "total": 43,
        "stale": 0,
        "by_source": {"greenhouse": 43},
    }
    mock_cache.query_active.return_value = []

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.WellfoundCollector") as mock_wf, \
         patch("run_jobagent.UniversalATSRacer") as mock_racer, \
         patch("run_jobagent.load_companies_from_file") as mock_companies, \
         patch("run_jobagent.filter_recent_jobs", return_value=[]), \
         patch("run_jobagent.enrich_recent_jobs_with_groq", return_value=[]), \
         patch("run_jobagent.rank_jobs", return_value=[]), \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
            "--mode", "cache_only",
        ]):
            main("r.pdf", non_interactive=True, mode="cache_only")

        mock_wf.assert_not_called()
        mock_racer.assert_not_called()
        mock_companies.assert_not_called()
        mock_cache.upsert.assert_not_called()
        mock_cache.query_active.assert_called_once()


def test_refresh_calls_collectors():
    """
    In refresh mode, collectors should be called and
    cache.upsert should be called with collected jobs.
    """
    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 0,
        "total": 0,
        "stale": 0,
        "by_source": {},
    }
    mock_cache.query_active.return_value = []

    mock_racer_instance = MagicMock()
    mock_racer_instance.collect_all.return_value = []

    mock_wf_instance = MagicMock()
    mock_wf_instance.collect.return_value = []

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.UniversalATSRacer", return_value=mock_racer_instance) as mock_racer_cls, \
         patch("run_jobagent.WellfoundCollector", return_value=mock_wf_instance) as mock_wf_cls, \
         patch("run_jobagent.load_companies_from_file", return_value=["Acme"]), \
         patch("run_jobagent.filter_recent_jobs", return_value=[]), \
         patch("run_jobagent.enrich_recent_jobs_with_groq", return_value=[]), \
         patch("run_jobagent.rank_jobs", return_value=[]), \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
            "--mode", "refresh",
        ]):
            main("r.pdf", non_interactive=True, mode="refresh")

        mock_racer_cls.assert_called_once()
        mock_wf_cls.assert_called_once()
        assert mock_cache.upsert.call_count == 2
        # mark_stale called for wellfound (successful collection)
        mock_cache.mark_stale.assert_called_once_with(
            "wellfound", set()
        )


def test_cache_only_empty_cache_exits_early():
    """
    When cache_only mode is requested but cache has zero
    active jobs, main() should return without calling the
    downstream pipeline.
    """
    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 0,
        "total": 0,
        "stale": 0,
        "by_source": {},
    }

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.filter_recent_jobs") as mock_filter, \
         patch("run_jobagent.enrich_recent_jobs_with_groq") as mock_enrich, \
         patch("run_jobagent.rank_jobs") as mock_rank, \
         patch("run_jobagent.EmailService") as mock_email, \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
            "--mode", "cache_only",
        ]):
            main("r.pdf", non_interactive=True, mode="cache_only")

        mock_filter.assert_not_called()
        mock_enrich.assert_not_called()
        mock_rank.assert_not_called()
        mock_email.assert_not_called()


def test_default_mode_is_refresh():
    """
    When no --mode is supplied, the default should be refresh
    and collectors should be called.
    """
    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 0,
        "total": 0,
        "stale": 0,
        "by_source": {},
    }
    mock_cache.query_active.return_value = []

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.UniversalATSRacer") as mock_racer, \
         patch("run_jobagent.WellfoundCollector") as mock_wf, \
         patch("run_jobagent.load_companies_from_file", return_value=["Acme"]), \
         patch("run_jobagent.filter_recent_jobs", return_value=[]), \
         patch("run_jobagent.enrich_recent_jobs_with_groq", return_value=[]), \
         patch("run_jobagent.rank_jobs", return_value=[]), \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
        ]):
            main("r.pdf", non_interactive=True, mode="refresh")

        mock_racer.assert_called()
        mock_wf.assert_called()


# ---------------------------------------------------------
# Regression: source-level persistence tests
# ---------------------------------------------------------


def test_ats_succeeds_wellfound_fails():
    """
    When Wellfound collection raises an exception, ATS jobs
    should still be written to the cache and the pipeline
    should continue without crashing.
    """
    from app.models.job import Job

    ats_jobs = [
        Job(
            id=str(i),
            title=f"Engineer {i}",
            company=f"Company {i}",
            source="greenhouse",
            application_url=f"https://greenhouse.com/{i}",
        )
        for i in range(5)
    ]

    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 5,
        "total": 5,
        "stale": 0,
        "by_source": {"greenhouse": 5},
    }
    mock_cache.query_active.return_value = ats_jobs

    mock_racer_instance = MagicMock()
    mock_racer_instance.collect_all.return_value = ats_jobs

    mock_wf_instance = MagicMock()
    mock_wf_instance.collect.side_effect = Exception(
        "Wellfound timeout"
    )

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.UniversalATSRacer", return_value=mock_racer_instance) as mock_racer_cls, \
         patch("run_jobagent.WellfoundCollector", return_value=mock_wf_instance) as mock_wf_cls, \
         patch("run_jobagent.load_companies_from_file", return_value=["Acme"]), \
         patch("run_jobagent.filter_recent_jobs", return_value=[]), \
         patch("run_jobagent.enrich_recent_jobs_with_groq", return_value=[]), \
         patch("run_jobagent.rank_jobs", return_value=[]), \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
            "--mode", "refresh",
        ]):
            main("r.pdf", non_interactive=True, mode="refresh")

        # Both collectors should be instantiated
        mock_racer_cls.assert_called_once()
        mock_wf_cls.assert_called_once()

        # Cache upsert called twice: ATS jobs, then empty Wellfound
        assert mock_cache.upsert.call_count == 2

        # First upsert contains the 5 ATS jobs
        first_args = mock_cache.upsert.call_args_list[0]
        assert len(first_args[0][0]) == 5

        # Second upsert is empty (Wellfound failed)
        second_args = mock_cache.upsert.call_args_list[1]
        assert len(second_args[0][0]) == 0

        # mark_stale must NOT be called automatically
        mock_cache.mark_stale.assert_not_called()


def test_both_collectors_succeed():
    """
    When both collectors succeed, jobs from both sources
    should be persisted independently and the pipeline
    should continue.
    """
    from app.models.job import Job

    ats_jobs = [
        Job(
            id="ats-1",
            title="Backend Engineer",
            company="Acme",
            source="greenhouse",
            application_url="https://greenhouse.com/1",
        ),
    ]

    wf_jobs = [
        Job(
            id="wf-1",
            title="AI Engineer",
            company="Startup",
            source="wellfound",
            application_url="https://wellfound.com/jobs/1",
        ),
    ]

    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 2,
        "total": 2,
        "stale": 0,
        "by_source": {"greenhouse": 1, "wellfound": 1},
    }
    mock_cache.query_active.return_value = ats_jobs + wf_jobs

    mock_racer_instance = MagicMock()
    mock_racer_instance.collect_all.return_value = ats_jobs

    mock_wf_instance = MagicMock()
    mock_wf_instance.collect.return_value = wf_jobs

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.UniversalATSRacer", return_value=mock_racer_instance), \
         patch("run_jobagent.WellfoundCollector", return_value=mock_wf_instance), \
         patch("run_jobagent.load_companies_from_file", return_value=["Acme"]), \
         patch("run_jobagent.filter_recent_jobs", return_value=[]), \
         patch("run_jobagent.enrich_recent_jobs_with_groq", return_value=[]), \
         patch("run_jobagent.rank_jobs", return_value=[]), \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
            "--mode", "refresh",
        ]):
            main("r.pdf", non_interactive=True, mode="refresh")

        # Both upserts should happen
        assert mock_cache.upsert.call_count == 2

        # First upsert: ATS jobs
        first_args = mock_cache.upsert.call_args_list[0]
        assert len(first_args[0][0]) == 1
        assert first_args[0][0][0].source == "greenhouse"

        # Second upsert: Wellfound jobs
        second_args = mock_cache.upsert.call_args_list[1]
        assert len(second_args[0][0]) == 1
        assert second_args[0][0][0].source == "wellfound"

        # mark_stale called for wellfound (successful collection)
        mock_cache.mark_stale.assert_called_once_with(
            "wellfound", {"wf-1"}
        )


def test_wellfound_empty_preserves_ats():
    """
    When Wellfound returns zero jobs (not a crash, just
    empty results), ATS jobs should still be in the cache
    and the pipeline should continue.
    """
    from app.models.job import Job

    ats_jobs = [
        Job(
            id="ats-1",
            title="Backend Engineer",
            company="Acme",
            source="greenhouse",
            application_url="https://greenhouse.com/1",
        ),
    ]

    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "active": 1,
        "total": 1,
        "stale": 0,
        "by_source": {"greenhouse": 1},
    }
    mock_cache.query_active.return_value = ats_jobs

    mock_racer_instance = MagicMock()
    mock_racer_instance.collect_all.return_value = ats_jobs

    mock_wf_instance = MagicMock()
    mock_wf_instance.collect.return_value = []

    with patch("run_jobagent.JobCache", return_value=mock_cache), \
         patch("run_jobagent.UniversalATSRacer", return_value=mock_racer_instance), \
         patch("run_jobagent.WellfoundCollector", return_value=mock_wf_instance), \
         patch("run_jobagent.load_companies_from_file", return_value=["Acme"]), \
         patch("run_jobagent.filter_recent_jobs", return_value=[]), \
         patch("run_jobagent.enrich_recent_jobs_with_groq", return_value=[]), \
         patch("run_jobagent.rank_jobs", return_value=[]), \
         patch("run_jobagent.extract_resume_text", return_value="resume text"), \
         patch("run_jobagent.build_candidate_profile") as mock_build:

        mock_build.return_value = CandidateProfile(
            resume_roles=["AI Engineer"],
        )

        with patch.object(sys, "argv", [
            "run_jobagent.py",
            "--resume", "r.pdf",
            "--non-interactive",
            "--mode", "refresh",
        ]):
            main("r.pdf", non_interactive=True, mode="refresh")

        # Both upserts should happen
        assert mock_cache.upsert.call_count == 2

        # First upsert: ATS jobs preserved
        first_args = mock_cache.upsert.call_args_list[0]
        assert len(first_args[0][0]) == 1
        assert first_args[0][0][0].id == "ats-1"

        # Second upsert: empty Wellfound
        second_args = mock_cache.upsert.call_args_list[1]
        assert len(second_args[0][0]) == 0

        # mark_stale called for wellfound (successful but empty
        # collection marks all cached wellfound jobs stale)
        mock_cache.mark_stale.assert_called_once_with(
            "wellfound", set()
        )


# ---------------------------------------------------------
# Stage 7 — Runner / User Preference Flow
# ---------------------------------------------------------


def test_interactive_preferences_populate_candidate_preferences():
    from run_jobagent import collect_explicit_preferences

    profile = CandidateProfile(
        resume_roles=["Data Engineer"],
        skills=["Python", "Spark"],
    )

    inputs = iter([
        "AI Engineer, Backend Engineer",   # primary roles
        "ML Engineer",                      # secondary roles
        "Bengaluru, Remote",               # locations
        "20",                               # salary
    ])
    with patch("builtins.input", side_effect=lambda _="": next(inputs)):
        result = collect_explicit_preferences(profile)

    assert result.preferences.preferred_roles == [
        "AI Engineer",
        "Backend Engineer",
    ]
    assert result.preferences.secondary_roles == [
        "ML Engineer",
    ]
    assert result.preferences.preferred_locations == [
        "Bengaluru",
        "Remote",
    ]
    assert result.preferences.minimum_salary_lpa == 20.0


def test_defaults_do_not_turn_resume_roles_into_preferences():
    profile = CandidateProfile(
        resume_roles=["AI Engineer", "Backend Engineer"],
        skills=["Python"],
    )

    apply_default_preferences(profile)

    assert profile.preferences.preferred_roles == []
    assert profile.preferences.secondary_roles == []
    assert profile.preferences.preferred_locations == []
    assert profile.preferences.minimum_salary_lpa is None
    assert profile.preferences.prefer_remote is None

    assert profile.facts.resume_roles == [
        "AI Engineer",
        "Backend Engineer",
    ]


def test_resume_facts_survive_preference_collection():
    from run_jobagent import collect_explicit_preferences

    profile = CandidateProfile(
        resume_roles=["ML Engineer"],
        skills=["Python", "PyTorch"],
        experience_years=2.5,
        career_level="mid",
        name="Test User",
    )

    inputs = iter([
        "Software Engineer",   # primary roles
        "",                     # secondary roles
        "",                     # locations
        "",                     # salary
    ])
    with patch("builtins.input", side_effect=lambda _="": next(inputs)):
        result = collect_explicit_preferences(profile)

    assert result.facts.resume_roles == ["ML Engineer"]
    assert result.facts.skills == ["Python", "PyTorch"]
    assert result.facts.experience_years == 2.5
    assert result.facts.career_level == "mid"
    assert result.facts.name == "Test User"


def test_unset_preferences_remain_unset():
    profile = CandidateProfile(
        resume_roles=["SDE"],
    )

    apply_default_preferences(profile)

    assert profile.preferences.preferred_roles == []
    assert profile.preferences.secondary_roles == []
    assert profile.preferences.preferred_locations == []
    assert profile.preferences.minimum_salary_lpa is None
    assert profile.preferences.prefer_remote is None


def test_non_interactive_does_not_invent_preferences():
    profile = CandidateProfile(
        resume_roles=["Backend Engineer"],
        skills=["Go", "PostgreSQL"],
    )

    apply_default_preferences(profile)

    assert profile.preferences.preferred_roles == []
    assert profile.preferences.preferred_locations == []
    assert profile.preferences.minimum_salary_lpa is None
    assert profile.preferences.prefer_remote is None

    assert profile.facts.resume_roles == ["Backend Engineer"]
    assert profile.facts.skills == ["Go", "PostgreSQL"]
