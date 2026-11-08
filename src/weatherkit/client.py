"""The weatherkit client."""
from .models import Forecast
from .providers.base import Provider
from .providers.fake import FakeProvider
from ._internal.cache import Cache


class Client:
    """Fetch forecasts from a provider.

    Args:
        provider: Data source; defaults to `FakeProvider`.
    """

    def __init__(self, provider: Provider | None = None):
        self.provider = provider or FakeProvider()
        self._cache = Cache()

    def forecast(self, city: str) -> Forecast:
        """Return the forecast for ``city``.

        Example:
            >>> Client().forecast("Oslo").city
            'Oslo'
        """
        return Forecast(city, self.provider.temperature(city))

    def undocumented(self): return 1
