"""Provider interface."""
import abc


class Provider(abc.ABC):
    """Abstract weather data source."""

    @abc.abstractmethod
    def temperature(self, city: str) -> float:
        """Return the temperature in Celsius."""
