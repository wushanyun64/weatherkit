# Getting started

In this tutorial you'll install weatherkit, get a forecast from Python, read its fields, and then
get the same forecast from the command line. It takes about five minutes.

**You'll need:** Python 3.10 or newer, `git`, and a terminal.

## Install weatherkit

Clone the repository and install it into a virtual environment:

```bash
git clone https://github.com/wushanyun64/weatherkit.git
cd weatherkit
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Get your first forecast

Create a file called `quickstart.py` with these lines (the same file is in the repository at
`examples/quickstart.py`):

```python
--8<-- "examples/quickstart.py"
```

Run it:

```bash
python quickstart.py
```

You should see:

```text
Forecast(city='Oslo', temp_c=21.5)
```

`Client()` created a client with the default provider, and `forecast("Oslo")` returned a `Forecast`
object for Oslo.

## Read the forecast's fields

A `Forecast` has two fields, `city` and `temp_c` (temperature in degrees Celsius). Read them
directly:

```python
from weatherkit import Client

forecast = Client().forecast("Oslo")
print(f"It's {forecast.temp_c} °C in {forecast.city}.")
```

```text
It's 21.5 °C in Oslo.
```

Try another city, like `"Lima"`. You'll get 21.5 °C again. That's expected: the default provider is
`FakeProvider`, which always returns the same temperature so results are predictable. You'll swap it
for real data in [How to use a custom provider](../how-to/custom-provider.md).

## Use the command line

Installing weatherkit also installed a `weatherkit` command. Pass it a city:

```bash
weatherkit Oslo
```

```text
Forecast(city='Oslo', temp_c=21.5)
```

## What you've learned

You created a `Client`, asked it for a forecast, read the `Forecast` fields, and ran the CLI.

**Next steps**

- [Use a custom provider](../how-to/custom-provider.md) to connect a real data source.
- Browse the [API reference](../reference/api/weatherkit/index.md) for every class and field.
- Read about the [architecture](../explanation/architecture.md) to see why providers are pluggable.
