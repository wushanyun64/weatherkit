"""Run every ```python code block in the docs and README as a test.

Blocks in one file share a namespace and run in order, like a reader following the page.
Snippet includes (--8<-- "path") are expanded first, so included example files are tested too.
Fence illustrative, non-runnable fragments as ```py or ```text so they are skipped.
Build-time blocks (```python exec="on") are skipped too; the docs build runs those.
"""

import pathlib
import re

import pytest
from mktestdocs import grab_code_blocks

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / "docs").glob("**/*.md")) + [ROOT / "README.md"]
SNIPPET = re.compile(r'^(\s*)--8<--\s+"([^"]+)"\s*$', re.MULTILINE)


def expand_snippets(text: str) -> str:
    def repl(m):
        for base in (ROOT, ROOT / "docs"):  # same base_path as zensical.toml
            path = base / m.group(2)
            if path.is_file():
                return "\n".join(m.group(1) + line for line in path.read_text().splitlines())
        raise FileNotFoundError(f"snippet not found: {m.group(2)}")

    return SNIPPET.sub(repl, text)


@pytest.mark.parametrize("fpath", [f for f in FILES if f.exists()], ids=lambda p: str(p.relative_to(ROOT)))
def test_markdown_code_blocks(fpath):
    blocks = grab_code_blocks(expand_snippets(fpath.read_text()), lang="python")
    if not blocks:
        pytest.skip("no ```python blocks")
    exec("\n".join(blocks), {"__name__": "__main__"})
