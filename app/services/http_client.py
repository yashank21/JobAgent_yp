"""
HTTP Client

Centralizes HTTP requests used by JobAgent collectors.
"""

import time

import requests


class HTTPClient:
    """HTTP client with retry support."""

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def get(self, url: str) -> dict:
        """
        Perform a GET request and return JSON data.

        Retries temporary failures such as:
        - timeouts
        - connection errors
        - HTTP 429
        - HTTP 5xx
        """

        last_error = None

        for attempt in range(self.max_retries + 1):

            try:

                response = requests.get(
                    url,
                    timeout=self.timeout,
                )

                if response.status_code == 429:
                    last_error = requests.HTTPError(
                        "Rate limited (HTTP 429)"
                    )

                elif response.status_code >= 500:
                    last_error = requests.HTTPError(
                        f"Server error (HTTP {response.status_code})"
                    )

                else:
                    response.raise_for_status()

                    return response.json()

            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.HTTPError,
            ) as error:

                last_error = error

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        raise last_error