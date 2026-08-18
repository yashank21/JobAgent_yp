from app.location.location_normalizer import (
    normalize_location,
    location_matches,
)


def test_india_city_normalizes_to_india():
    assert normalize_location("Bengaluru, India") == "India"


def test_india_city_with_country_normalizes_to_india():
    assert normalize_location("Pune, Maharashtra, India") == "India"


def test_us_city_normalizes_to_united_states():
    assert normalize_location("Hawthorne, CA") == "United States"


def test_us_city_with_state_normalizes_to_united_states():
    assert normalize_location("Redmond, WA") == "United States"


def test_texas_location_normalizes_to_united_states():
    assert normalize_location("Starbase, TX") == "United States"


def test_remote_location_normalizes_to_remote():
    assert normalize_location("Remote") == "Remote"


def test_remote_type_is_recognized():
    assert normalize_location("Remote - United States") == "Remote"


def test_india_matches_india_preference():
    assert location_matches(
        "Bengaluru, India",
        ["India"],
    )


def test_us_city_matches_united_states_preference():
    assert location_matches(
        "Hawthorne, CA",
        ["United States"],
    )


def test_india_does_not_match_united_states():
    assert not location_matches(
        "Bengaluru, India",
        ["United States"],
    )


def test_remote_matches_remote_preference():
    assert location_matches(
        "Remote",
        ["Remote"],
    )


def test_empty_preferences_allow_any_location():
    assert location_matches(
        "Hawthorne, CA",
        [],
    )