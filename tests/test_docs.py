"""Run every ```python code block in the docs and README as a test.

Fence illustrative, non-runnable fragments as ```py or ```text so they are skipped.
"""

import pathlib

import pytest
from mktestdocs import check_md_file

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / "docs").glob("**/*.md")) + [ROOT / "README.md"]


@pytest.mark.parametrize("fpath", [f for f in FILES if f.exists()], ids=lambda p: str(p.relative_to(ROOT)))
def test_markdown_code_blocks(fpath):
    check_md_file(fpath=fpath, memory=True)
