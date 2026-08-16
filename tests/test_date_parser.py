from datetime import datetime

from app.services.date_parser import parse_greenhouse_date


def test_parse_greenhouse_date():

    value = "2026-07-21T19:49:28-04:00"

    result = parse_greenhouse_date(value)

    assert result == datetime.fromisoformat(value)


def test_parse_greenhouse_date_empty():

    assert parse_greenhouse_date("") is None


def test_parse_greenhouse_date_invalid():

    assert parse_greenhouse_date(
        "not-a-date"
    ) is None