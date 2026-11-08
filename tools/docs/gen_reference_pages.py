"""Generate API reference pages and code diagrams at `mkdocs build` time (document-it skill).

Run by the mkdocs-gen-files plugin (see mkdocs.yml). Everything it writes is virtual: nothing
lands in docs/, nothing is committed, so the reference can never drift from the code.

Outputs:
  reference/api/**.md       one `::: module` page per public module (rendered by mkdocstrings)
  reference/api/SUMMARY.md  nav for mkdocs-literate-nav
  reference/diagrams.md     import graph + class hierarchy (SVG via Graphviz, else Mermaid)

Configuration via environment variables (all optional):
  DOCS_SRC              source root containing the packages (default: src/ if present, else .)
  DOCS_PACKAGES         comma-separated top-level packages to document (default: all found)
  DOCS_EXCLUDE          comma-separated top-level names to skip
  DOCS_INCLUDE_PRIVATE  1 to include _private modules (default: 0)
  DOCS_DIAGRAMS         0 to skip the diagrams page (default: 1)
  DOCS_DIAGRAM_MAX_NODES  collapse graphs larger than this (default: 40)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import mkdocs_gen_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] if (HERE.parents[1] / "mkdocs.yml").exists() else Path.cwd()
sys.path.insert(0, str(HERE))
import gen_diagrams  # noqa: E402  (sibling module copied alongside this script)

src = ROOT / os.environ["DOCS_SRC"] if os.environ.get("DOCS_SRC") else gen_diagrams.default_src(ROOT)
packages = [p for p in os.environ.get("DOCS_PACKAGES", "").split(",") if p] or None
exclude = set(filter(None, os.environ.get("DOCS_EXCLUDE", "").split(","))) or gen_diagrams.DEFAULT_EXCLUDE
include_private = os.environ.get("DOCS_INCLUDE_PRIVATE") == "1"

modules = gen_diagrams.discover(src, packages, exclude, include_private)
if not modules:
    print(f"gen_reference_pages: no Python packages found under {src}", file=sys.stderr)

nav = mkdocs_gen_files.Nav()
for mod in modules:
    parts = tuple(mod.name.split("."))
    doc_path = Path(*parts, "index.md") if mod.is_package else Path(*parts[:-1], f"{parts[-1]}.md")
    nav[parts] = doc_path.as_posix()
    with mkdocs_gen_files.open(Path("reference/api", doc_path), "w") as fd:
        fd.write(f"::: {mod.name}\n")
    mkdocs_gen_files.set_edit_path(Path("reference/api", doc_path), mod.path.relative_to(ROOT))

# API landing page, so `reference/api/index.md` always exists for links and nav.
with mkdocs_gen_files.open("reference/api/index.md", "w") as fd:
    fd.write("# API reference\n\nGenerated from the source code on every build.\n\n")
    fd.writelines(f"- [`{m.name}`]({m.name}/index.md)\n" for m in modules if "." not in m.name)

with mkdocs_gen_files.open("reference/api/SUMMARY.md", "w") as fd:
    fd.write("* [Overview](index.md)\n")
    fd.writelines(nav.build_literate_nav())

if os.environ.get("DOCS_DIAGRAMS", "1") != "0":
    has_explanation = (ROOT / "docs" / "explanation" / "index.md").exists()
    page, assets = gen_diagrams.build_page(
        src, packages, exclude, include_private,
        max_nodes=int(os.environ.get("DOCS_DIAGRAM_MAX_NODES", 40)),
        explanation_link="../explanation/index.md" if has_explanation else None,
    )
    with mkdocs_gen_files.open("reference/diagrams.md", "w") as fd:
        fd.write(page)
    for name, data in assets.items():
        with mkdocs_gen_files.open(f"reference/{name}", "wb") as fd:
            fd.write(data)
