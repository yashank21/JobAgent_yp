from app.services.experience_parser import parse_experience_years


def test_parse_plus_years():
    assert parse_experience_years(
        "2+ years of software development experience"
    ) == 2.0


def test_parse_exact_years():
    assert parse_experience_years(
        "3 years of experience"
    ) == 3.0


def test_parse_year_range():
    assert parse_experience_years(
        "1-3 years of experience"
    ) == 1.0


def test_parse_year_to_year_range():
    assert parse_experience_years(
        "2 to 5 years of experience"
    ) == 2.0


def test_parse_decimal_years():
    assert parse_experience_years(
        "1.5 years of experience"
    ) == 1.5


def test_no_experience_requirement():
    assert parse_experience_years(
        "Bachelor's degree in Computer Science"
    ) is None

def test_parse_months():
    assert parse_experience_years(
        "11 months of experience"
    ) == 11 / 12


def test_parse_months_with_plus():
    assert parse_experience_years(
        "6+ months of experience"
    ) == 6 / 12


def test_empty_text():
    assert parse_experience_years("") is None