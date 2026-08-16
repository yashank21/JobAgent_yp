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