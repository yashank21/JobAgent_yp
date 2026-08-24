"""Utilities for loading JobAgent company configuration."""


def load_companies_from_file(
    filepath: str = "companies.txt",
) -> list[str]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [
                line.strip()
                for line in f
                if line.strip()
                and not line.lstrip().startswith("#")
            ]
    except FileNotFoundError:
        raise RuntimeError(
            f"{filepath} not found. "
            "JobAgent requires companies.txt in the project root."
        )