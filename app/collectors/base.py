"""
Base collector interface.

Every job collector must implement this interface.
"""

from abc import ABC, abstractmethod

from app.models.job import Job


class BaseCollector(ABC):
    """Base interface for all job collectors."""

    @abstractmethod
    def collect(self) -> list[Job]:
        """
        Collect jobs and return them in our standard Job format.
        """
        pass