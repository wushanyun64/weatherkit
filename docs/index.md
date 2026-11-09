# weatherkit

weatherkit is a tiny Python weather client. You ask a `Client` for a city's forecast, and it returns
a `Forecast` from a pluggable data source called a *provider*. It's for Python developers who want a
small, typed interface for weather data that's easy to swap out in tests.

```bash
pip install -e .   # from a clone of the repository
```

```python
from weatherkit import Client

forecast = Client().forecast("Oslo")
print(forecast.city, forecast.temp_c)
```

```text
Oslo 21.5
```

The default provider is a deterministic fake that always returns 21.5 °C. To use real data,
[plug in your own provider](how-to/custom-provider.md).

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Tutorials**

    ---

    New here? Get your first forecast from Python and from the command line.

    [:octicons-arrow-right-24: Getting started](tutorials/getting-started.md)

-   :material-hammer-wrench:{ .lg .middle } **How-to guides**

    ---

    Connect your own data source, and make tests deterministic.

    [:octicons-arrow-right-24: How-to guides](how-to/index.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Generated description of the API, the CLI, and the module structure.

    [:octicons-arrow-right-24: Reference](reference/index.md)

-   :material-lightbulb-on:{ .lg .middle } **Explanation**

    ---

    How the client, providers, and models fit together, and why.

    [:octicons-arrow-right-24: Architecture](explanation/architecture.md)

</div>
