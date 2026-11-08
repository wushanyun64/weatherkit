"""Deterministic provider for tests and demos."""
from .base import Provider


class FakeProvider(Provider):
    """Returns a fixed temperature."""

    def temperature(self, city: str) -> float:
        """Always 21.5."""
        return 21.5
