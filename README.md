# weatherkit

Tiny weather client.

> **This is a demo repository.** `weatherkit` is a toy package used to show what the
> [document-it](https://github.com/wushanyun64/document-it) agent skill produces: a Diátaxis
> documentation site built with [Zensical](https://zensical.org/), published to GitHub Pages, with
> CI that keeps the docs in sync with the code.
>
> **Live docs:** https://wushanyun64.github.io/weatherkit/

## What document-it added here

- `zensical.toml`, `requirements-docs.txt`: site config and the pinned docs toolchain
- `docs/`: the doc set (tutorials, how-to guides, reference, explanation) and `docs/.doc-spec.yml`
- `docs/reference/`: the API reference is generated from docstrings, the diagrams page from the
  code's import graph and class hierarchy, and the CLI page from `weatherkit --help`, all at build time
- `tools/docs/`: `gen_diagrams.py` and `check_drift.py`
- `tests/test_docs.py`: runs the Python examples in the docs
- `.github/workflows/docs-deploy.yml`: builds and deploys to GitHub Pages on every push to `main`
- `.github/workflows/docs-check.yml`: on pull requests, runs a strict build, link check, doc
  example tests, and a drift check that flags public API changes without docs changes

The optional AI doc-update workflow isn't enabled in this demo, because it needs an API key secret.

## Usage

```bash
pip install -e .
weatherkit Oslo
```

## Build the docs locally

```bash
pip install -r requirements-docs.txt -e .
zensical build --clean --strict
zensical serve   # http://localhost:8000
```
