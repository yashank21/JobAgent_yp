import sys
from unittest.mock import patch

from app.models.candidate import CandidateProfile
from run_jobagent import (
    apply_default_preferences,
    parse_args,
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


def test_parse_args_non_interactive_flag():
    args = _parse(
        ["--resume", "r.pdf", "--non-interactive"]
    )
    assert args.resume == "r.pdf"
    assert args.non_interactive is True


def test_apply_default_preferences_uses_resume_roles():
    profile = CandidateProfile(
        resume_roles=["AI Engineer", "Backend Engineer"],
    )

    result = apply_default_preferences(profile)

    assert result.preferred_roles == [
        "AI Engineer",
        "Backend Engineer",
    ]
    assert result is profile


def test_apply_default_preferences_empty_roles():
    profile = CandidateProfile(resume_roles=[])

    result = apply_default_preferences(profile)

    assert result.preferred_roles == []
    assert result is profile


def test_apply_default_preferences_does_not_touch_other_fields():
    profile = CandidateProfile(
        resume_roles=["ML Engineer"],
        preferred_locations=["India"],
        minimum_salary_lpa=15.0,
        skills=["Python", "PyTorch"],
    )

    apply_default_preferences(profile)

    assert profile.preferred_locations == ["India"]
    assert profile.minimum_salary_lpa == 15.0
    assert profile.skills == ["Python", "PyTorch"]


def test_non_interactive_does_not_call_input(capsys):
    profile = CandidateProfile(
        resume_roles=["SDE", "Software Engineer"],
    )

    result = apply_default_preferences(profile)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.preferred_roles == ["SDE", "Software Engineer"]
