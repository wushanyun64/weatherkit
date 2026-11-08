"""Data models."""
from dataclasses import dataclass


@dataclass
class Forecast:
    """A forecast for one city.

    Attributes:
        city: City name.
        temp_c: Temperature in Celsius.
    """
    city: str
    temp_c: float
