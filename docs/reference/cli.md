# CLI

The `weatherkit` command prints the forecast for one city using the default provider
(`FakeProvider`). It has no options for choosing a provider; use the
[Python API](api/weatherkit/client.md) for that.

## Usage

The help text below is captured from `weatherkit --help` when the docs are built.

```bash exec="on" result="text"
weatherkit --help
```

## Arguments

| Argument | Required | Description |
|---|---|---|
| `city` | yes | Name of the city to get a forecast for. |

## Output

The command prints the `Forecast` object and exits with status 0:

```console
$ weatherkit Oslo
Forecast(city='Oslo', temp_c=21.5)
```
