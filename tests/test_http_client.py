from unittest.mock import Mock, patch

import requests

from app.services.http_client import HTTPClient


def test_http_client_initialization():

    client = HTTPClient(
        timeout=5,
        max_retries=2,
        retry_delay=0,
    )

    assert client.timeout == 5
    assert client.max_retries == 2
    assert client.retry_delay == 0


@patch("app.services.http_client.requests.get")
def test_http_client_retries_on_server_error(mock_get):

    failed_response = Mock()
    failed_response.status_code = 500

    successful_response = Mock()
    successful_response.status_code = 200
    successful_response.json.return_value = {
        "jobs": []
    }

    mock_get.side_effect = [
        failed_response,
        failed_response,
        successful_response,
    ]

    client = HTTPClient(
        timeout=5,
        max_retries=2,
        retry_delay=0,
    )

    result = client.get("https://example.com/jobs")

    assert result == {"jobs": []}

    assert mock_get.call_count == 3
    
from unittest.mock import Mock, patch

import requests

from app.services.http_client import HTTPClient


def test_http_client_initialization():

    client = HTTPClient(
        timeout=5,
        max_retries=2,
        retry_delay=0,
    )

    assert client.timeout == 5
    assert client.max_retries == 2
    assert client.retry_delay == 0


@patch("app.services.http_client.requests.get")
def test_http_client_retries_on_server_error(mock_get):

    failed_response = Mock()
    failed_response.status_code = 500

    successful_response = Mock()
    successful_response.status_code = 200
    successful_response.json.return_value = {
        "jobs": []
    }

    mock_get.side_effect = [
        failed_response,
        failed_response,
        successful_response,
    ]

    client = HTTPClient(
        timeout=5,
        max_retries=2,
        retry_delay=0,
    )

    result = client.get(
        "https://example.com/jobs"
    )

    assert result == {"jobs": []}

    assert mock_get.call_count == 3


@patch("app.services.http_client.requests.get")
def test_http_client_returns_json(mock_get):

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "jobs": [
            {
                "title": "Software Engineer"
            }
        ]
    }

    mock_get.return_value = response

    client = HTTPClient(
        retry_delay=0,
    )

    result = client.get(
        "https://example.com/jobs"
    )

    assert result == {
        "jobs": [
            {
                "title": "Software Engineer"
            }
        ]
    }


@patch("app.services.http_client.requests.get")
def test_http_client_returns_text_for_html(mock_get):

    response = Mock()
    response.status_code = 200

    response.json.side_effect = ValueError(
        "Not JSON"
    )

    response.text = (
        "<html>"
        "<body>"
        "Software Engineer"
        "</body>"
        "</html>"
    )

    mock_get.return_value = response

    client = HTTPClient(
        retry_delay=0,
    )

    result = client.get(
        "https://example.com/jobs"
    )

    assert result == (
        "<html>"
        "<body>"
        "Software Engineer"
        "</body>"
        "</html>"
    )


@patch("app.services.http_client.requests.get")
def test_http_client_passes_headers(mock_get):

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "jobs": []
    }

    mock_get.return_value = response

    client = HTTPClient(
        retry_delay=0,
    )

    headers = {
        "User-Agent": "JobAgent/1.0"
    }

    client.get(
        "https://example.com/jobs",
        headers=headers,
    )

    mock_get.assert_called_once_with(
        "https://example.com/jobs",
        headers=headers,
        params=None,
        timeout=10,
    )


@patch("app.services.http_client.requests.post")
def test_http_client_post_returns_json_and_passes_payload(mock_post):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"jobPostings": []}
    mock_post.return_value = response

    client = HTTPClient(retry_delay=0)
    payload = {"limit": 20, "offset": 0}
    headers = {"Content-Type": "application/json"}

    result = client.post(
        "https://example.com/jobs",
        json=payload,
        headers=headers,
    )

    assert result == {"jobPostings": []}
    mock_post.assert_called_once_with(
        "https://example.com/jobs",
        json=payload,
        headers=headers,
        timeout=10,
    )


@patch("app.services.http_client.requests.get")
def test_http_client_passes_query_parameters(mock_get):

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "jobs": []
    }

    mock_get.return_value = response

    client = HTTPClient(
        retry_delay=0,
    )

    params = {
        "page": "1",
        "limit": "10",
    }

    client.get(
        "https://example.com/jobs",
        params=params,
    )

    mock_get.assert_called_once_with(
        "https://example.com/jobs",
        headers=None,
        params=params,
        timeout=10,
    )


@patch("app.services.http_client.requests.get")
def test_http_client_retries_on_timeout(mock_get):

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "jobs": []
    }

    mock_get.side_effect = [
        requests.Timeout(),
        response,
    ]

    client = HTTPClient(
        max_retries=1,
        retry_delay=0,
    )

    result = client.get(
        "https://example.com/jobs"
    )

    assert result == {
        "jobs": []
    }

    assert mock_get.call_count == 2


@patch("app.services.http_client.requests.get")
def test_http_client_retries_on_rate_limit(mock_get):

    rate_limited = Mock()
    rate_limited.status_code = 429

    successful_response = Mock()
    successful_response.status_code = 200
    successful_response.json.return_value = {
        "jobs": []
    }

    mock_get.side_effect = [
        rate_limited,
        successful_response,
    ]

    client = HTTPClient(
        max_retries=1,
        retry_delay=0,
    )

    result = client.get(
        "https://example.com/jobs"
    )

    assert result == {
        "jobs": []
    }

    assert mock_get.call_count == 2


@patch("app.services.http_client.requests.get")
def test_http_client_raises_after_all_retries_fail(mock_get):

    failed_response = Mock()
    failed_response.status_code = 500

    mock_get.return_value = failed_response

    client = HTTPClient(
        max_retries=2,
        retry_delay=0,
    )

    try:
        client.get(
            "https://example.com/jobs"
        )

        assert False, (
            "Expected HTTPError to be raised"
        )

    except requests.HTTPError as error:

        assert "Server error" in str(error)

    assert mock_get.call_count == 3