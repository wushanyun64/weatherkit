# How to test with providers

Use this guide when you're writing tests for code that uses weatherkit and need the forecasts to be
predictable, with no network access.

**Prerequisites:** completed [Getting started](../tutorials/getting-started.md); `pytest` or another
test runner.

## Option A: Use `FakeProvider` for a fixed temperature

`FakeProvider` always returns 21.5 °C for every city. It's also what `Client()` uses when you don't
pass a provider, but passing it explicitly makes the test's intent clear:

```python
from weatherkit import Client
from weatherkit.providers.fake import FakeProvider


def test_forecast_uses_fixed_temperature():
    client = Client(provider=FakeProvider())
    assert client.forecast("Oslo").temp_c == 21.5


test_forecast_uses_fixed_temperature()
```

## Option B: Use a stub provider for specific values

When the code under test behaves differently depending on the temperature, write a small stub
provider that returns the value each test needs:

```python
from weatherkit import Client
from weatherkit.providers.base import Provider


class StubProvider(Provider):
    def __init__(self, temp_c: float):
        self.temp_c = temp_c

    def temperature(self, city: str) -> float:
        return self.temp_c


def describe(client: Client, city: str) -> str:
    """Code under test: turns a forecast into a short description."""
    return "cold" if client.forecast(city).temp_c < 10 else "mild"


def test_describe_cold():
    assert describe(Client(provider=StubProvider(-3.0)), "Oslo") == "cold"


def test_describe_mild():
    assert describe(Client(provider=StubProvider(18.0)), "Oslo") == "mild"


test_describe_cold()
test_describe_mild()
```

## Verify

Save either example as a `test_*.py` file (without the direct test calls at the bottom) and run
`pytest`. All tests pass.

## Related

- [How to use a custom provider](custom-provider.md)
- [`FakeProvider` API reference](../reference/api/weatherkit/providers/fake.md)
