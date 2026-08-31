"""
Centralized Groq API client for JobAgent.
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class GroqClient:
    """Small wrapper around the Groq API."""

    def __init__(
        self,
        *,
        model: str | None = None,
        max_retries: int = 2,
        retry_delay: float = 2.0,
    ) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        self.model = (
            model
            or os.getenv(
                "GROQ_MODEL",
                "openai/gpt-oss-20b",
            )
        )

        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.client = Groq(
            api_key=api_key,
        )

    def generate(
        self,
        prompt: str,
    ) -> str:
        """Generate text with retry handling."""

        if not prompt.strip():
            raise ValueError(
                "Groq prompt cannot be empty."
            )

        last_error = None

        for attempt in range(
            self.max_retries + 1
        ):
            try:
                response = (
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                    )
                )

                text = (
                    response.choices[0]
                    .message
                    .content
                )

                if not text:
                    raise RuntimeError(
                        "Groq returned an empty response."
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
            f"Groq request failed after "
            f"{self.max_retries + 1} attempts: "
            f"{last_error}"
        )


def get_groq_client() -> GroqClient:
    """Create the default JobAgent Groq client."""
    return GroqClient()
