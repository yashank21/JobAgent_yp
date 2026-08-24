"""
Centralized Gemini API client for JobAgent.
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiClient:
    """Small wrapper around the Google Gemini API."""

    def __init__(
        self,
        *,
        model: str | None = None,
        max_retries: int = 2,
        retry_delay: float = 1.5,
    ) -> None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                "gemini-3.6-flash",
            )
        )

        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.client = genai.Client(
            api_key=api_key,
        )

    def generate(
        self,
        prompt: str,
    ) -> str:
        """Generate text with retry handling."""

        if not prompt.strip():
            raise ValueError(
                "Gemini prompt cannot be empty."
            )

        last_error = None

        for attempt in range(
            self.max_retries + 1
        ):
            try:
                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                    )
                )

                text = getattr(
                    response,
                    "text",
                    None,
                )

                if not text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return text.strip()

            except Exception as exc:
                last_error = exc

                if attempt >= self.max_retries:
                    break

                time.sleep(
                    self.retry_delay * (attempt + 1)
                )

        raise RuntimeError(
            f"Gemini request failed after "
            f"{self.max_retries + 1} attempts: "
            f"{last_error}"
        )


def get_gemini_client() -> GeminiClient:
    """Create the default JobAgent Gemini client."""
    return GeminiClient()