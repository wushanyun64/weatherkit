#!/usr/bin/env python3
"""Generate architecture diagrams from Python source (document-it skill).

Produces an internal import graph and a class-inheritance graph by static analysis (ast);
no project code is imported or executed. Renders SVG with Graphviz `dot` when available,
otherwise emits Mermaid so docs builds never break.

Used two ways:
  * Docs build: docs/reference/diagrams.md calls render_from_env() in a markdown-exec block,
    so `zensical build` regenerates the diagrams every time (nothing is committed).
  * CLI:        python3 gen_diagrams.py --src src --out diagrams/ --format svg|dot|mermaid|md
"""

from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_EXCLUDE = {"tests", "test", "docs", "tools", "examples", "scripts", "benchmarks"}


@dataclass
class Module:
    name: str
    path: Path
    is_package: bool
    tree: ast.Module | None = field(default=None, repr=False)


def default_src(root: Path = Path(".")) -> Path:
    src = root / "src"
    return src if src.is_dir() else root


def discover(src: Path, packages: list[str] | None = None, exclude: set[str] | None = None,
             include_private: bool = False) -> list[Module]:
    """Find modules of the top-level packages under ``src``."""
    exclude = DEFAULT_EXCLUDE if exclude is None else exclude
    tops = [
        d for d in sorted(src.iterdir())
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in exclude
        and (not packages or d.name in packages)
    ]
    mods = []
    for top in tops:
        for path in sorted(top.rglob("*.py")):
            parts = list(path.relative_to(src).with_suffix("").parts)
            if "__pycache__" in parts or parts[-1] == "__main__":
                continue
            is_pkg = parts[-1] == "__init__"
            if is_pkg:
                parts = parts[:-1]
            if not include_private and any(p.startswith("_") for p in parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                tree = None
            mods.append(Module(".".join(parts), path, is_pkg, tree))
    return mods


def _resolve_relative(mod: Module, level: int, target: str | None) -> str:
    base = mod.name.split(".")
    if not mod.is_package:
        base = base[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join(base + ([target] if target else []))


def _closest(name: str, known: set[str]) -> str | None:
    """Longest known module that is ``name`` or a parent of it."""
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in known:
            return cand
    return None


def import_edges(mods: list[Module]) -> set[tuple[str, str]]:
    known = {m.name for m in mods}
    edges = set()
    for m in mods:
        if m.tree is None:
            continue
        for node in ast.walk(m.tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_relative(m, node.level, node.module) if node.level else (node.module or "")
                # `from pkg import submodule` should point at the submodule when it exists
                targets = [f"{base}.{a.name}" if f"{base}.{a.name}" in known else base for a in node.names]
            for t in targets:
                hit = _closest(t, known)
                # importing an excluded private module must not show up as an edge to its parent
                if hit and any(p.startswith("_") for p in t.split(".")[hit.count(".") + 1:]):
                    continue
                if hit and hit != m.name:
                    edges.add((m.name, hit))
    return edges


def class_edges(mods: list[Module]) -> tuple[set[tuple[str, str]], set[str]]:
    """(subclass, base) edges between classes defined in the scanned modules."""
    known_mods = {m.name for m in mods}
    defined: dict[str, set[str]] = {}
    for m in mods:
        if m.tree is not None:
            defined[m.name] = {n.name for n in m.tree.body if isinstance(n, ast.ClassDef)}
    all_classes = {f"{mod}.{c}" for mod, cs in defined.items() for c in cs}

    edges = set()
    for m in mods:
        if m.tree is None:
            continue
        aliases: dict[str, str] = {}  # local name -> qualified name
        for node in m.tree.body:
            if isinstance(node, ast.ImportFrom):
                base = _resolve_relative(m, node.level, node.module) if node.level else (node.module or "")
                for a in node.names:
                    aliases[a.asname or a.name] = f"{base}.{a.name}"
            elif isinstance(node, ast.Import):
                for a in node.names:
                    aliases[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        for node in m.tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            sub = f"{m.name}.{node.name}"
            for b in node.bases:
                if isinstance(b, ast.Name):
                    q = f"{m.name}.{b.id}" if b.id in defined.get(m.name, ()) else aliases.get(b.id, "")
                elif isinstance(b, ast.Attribute) and isinstance(b.value, ast.Name):
                    q = f"{aliases.get(b.value.id, b.value.id)}.{b.attr}"
                else:
                    continue
                if q not in all_classes:
                    # re-exported via a package __init__: find the defining module
                    head, _, cls = q.rpartition(".")
                    q = next((f"{mod}.{cls}" for mod in known_mods if mod.startswith(head) and cls in defined.get(mod, ())), q)
                if q in all_classes:
                    edges.add((sub, q))
    nodes = {n for e in edges for n in e}
    return edges, nodes


def collapse(edges: set[tuple[str, str]], depth: int) -> set[tuple[str, str]]:
    cut = lambda n: ".".join(n.split(".")[:depth])  # noqa: E731
    return {(cut(a), cut(b)) for a, b in edges if cut(a) != cut(b)}


def fit(edges: set[tuple[str, str]], max_nodes: int) -> tuple[set[tuple[str, str]], str | None]:
    """Collapse module names to shallower package levels until the graph fits."""
    nodes = {n for e in edges for n in e}
    if len(nodes) <= max_nodes:
        return edges, None
    deepest = max(n.count(".") + 1 for n in nodes)
    for depth in range(deepest - 1, 0, -1):
        small = collapse(edges, depth)
        if len({n for e in small for n in e}) <= max_nodes:
            return small, f"collapsed to package depth {depth} ({len(nodes)} modules)"
    return collapse(edges, 1), f"collapsed to top-level packages ({len(nodes)} modules)"


def _id(name: str) -> str:
    return "n_" + "".join(c if c.isalnum() else "_" for c in name)


def to_dot(edges: set[tuple[str, str]], label: str = "imports", rankdir: str = "LR") -> str:
    nodes = sorted({n for e in edges for n in e})
    lines = [
        "digraph G {",
        f'  rankdir={rankdir}; bgcolor="transparent"; nodesep=0.3; ranksep=0.6;',
        '  node [shape=box, style="rounded,filled", fillcolor="#eef2ff", color="#4f46e5", fontname="Helvetica", fontsize=11];',
        '  edge [color="#6b7280", arrowsize=0.7, fontname="Helvetica", fontsize=9];',
    ]
    lines += [f'  {_id(n)} [label="{n}"];' for n in nodes]
    lines += [f'  {_id(a)} -> {_id(b)} [tooltip="{label}"];' for a, b in sorted(edges)]
    lines.append("}")
    return "\n".join(lines)


def to_mermaid(edges: set[tuple[str, str]], verb: str, direction: str = "LR") -> str:
    nodes = sorted({n for e in edges for n in e})
    lines = [f"flowchart {direction}"]
    lines += [f'    {_id(n)}["{n}"]' for n in nodes]
    lines += [f"    {_id(a)} -->|{verb}| {_id(b)}" for a, b in sorted(edges)]
    return "\n".join(lines)


def render_svg(dot_source: str) -> bytes | None:
    dot = shutil.which("dot")
    if not dot:
        return None
    try:
        out = subprocess.run([dot, "-Tsvg"], input=dot_source.encode(), capture_output=True, timeout=60, check=True)
    except (subprocess.SubprocessError, OSError):
        return None
    return out.stdout


def build_page(src: Path, packages: list[str] | None = None, exclude: set[str] | None = None,
               include_private: bool = False, max_nodes: int = 40,
               explanation_link: str | None = "../explanation/index.md",
               inline_svg: bool = False, heading: bool = True) -> tuple[str, dict[str, bytes]]:
    """Return (markdown, {relative_asset_name: bytes}) for a 'Diagrams' reference page.

    With ``inline_svg`` the SVG markup is embedded in the Markdown and no assets are returned
    (used when rendering inside the docs build via markdown-exec). ``heading=False`` omits the
    title and intro so the caller's page can provide them.
    """
    mods = discover(src, packages, exclude, include_private)
    assets: dict[str, bytes] = {}
    md = []
    if heading:
        md += [
            "# Diagrams",
            "",
            "These diagrams are **generated from the source code on every docs build**, so they always",
            "reflect the current structure.",
        ]
        if explanation_link:
            md.append(f"For the intended design and the reasoning behind it, see [Explanation]({explanation_link}).")
        md.append("")
    graphs = [
        ("Module dependencies", "imports", "An arrow from A to B means module A imports module B.",
         *fit(import_edges(mods), max_nodes), "LR"),
        ("Class hierarchy", "inherits", "An arrow from A to B means class A subclasses class B.",
         *fit(class_edges(mods)[0], max_nodes), "BT"),
    ]
    for title, verb, caption, edges, note, direction in graphs:
        md += [f"## {title}", ""]
        if not edges:
            md += [f"*No internal {verb} relationships found.*", ""]
            continue
        slug = title.lower().replace(" ", "-")
        svg = render_svg(to_dot(edges, verb, "LR" if direction == "LR" else "BT"))
        if svg and inline_svg:
            markup = svg.decode("utf-8")
            markup = markup[markup.find("<svg"):].replace("\n", " ")  # drop XML prologue; one line keeps Markdown from re-parsing it
            md += [f'<div class="generated-diagram" role="img" aria-label="{title}: {caption}">{markup}</div>', ""]
        elif svg:
            assets[f"{slug}.svg"] = svg
            md += [f"![{title}: {caption}]({slug}.svg)", ""]
        else:
            md += ["```mermaid", to_mermaid(edges, verb, direction), "```", ""]
        md += [f"*{caption}*" + (f" ({note}.)" if note else ""), ""]
    return "\n".join(md), assets


def render_from_env() -> str:
    """Markdown body for the docs' Diagrams page, configured by DOCS_* environment variables.

    Called from a markdown-exec block in docs/reference/diagrams.md during `zensical build`.
    """
    src = Path(os.environ["DOCS_SRC"]) if os.environ.get("DOCS_SRC") else default_src()
    packages = [p for p in os.environ.get("DOCS_PACKAGES", "").split(",") if p] or None
    exclude = set(filter(None, os.environ.get("DOCS_EXCLUDE", "").split(","))) or None
    return build_page(
        src, packages, exclude,
        include_private=os.environ.get("DOCS_INCLUDE_PRIVATE") == "1",
        max_nodes=int(os.environ.get("DOCS_DIAGRAM_MAX_NODES", 40)),
        inline_svg=True, heading=False,
    )[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=None, help="source root containing packages (default: src/ or .)")
    ap.add_argument("--packages", default="", help="comma-separated top-level packages (default: all)")
    ap.add_argument("--out", type=Path, required=True, help="output directory")
    ap.add_argument("--format", choices=["svg", "dot", "mermaid", "md"], default="svg")
    ap.add_argument("--max-nodes", type=int, default=int(os.environ.get("DOCS_DIAGRAM_MAX_NODES", 40)))
    ap.add_argument("--include-private", action="store_true")
    args = ap.parse_args()

    src = args.src or default_src()
    pkgs = [p for p in args.packages.split(",") if p] or None
    args.out.mkdir(parents=True, exist_ok=True)
    if args.format == "md":
        md, assets = build_page(src, pkgs, include_private=args.include_private, max_nodes=args.max_nodes)
        (args.out / "diagrams.md").write_text(md, encoding="utf-8")
        for name, data in assets.items():
            (args.out / name).write_bytes(data)
        print(f"wrote {args.out / 'diagrams.md'} + {len(assets)} asset(s)")
        return 0

    mods = discover(src, pkgs, include_private=args.include_private)
    for name, edges, verb, direction in [
        ("module-dependencies", import_edges(mods), "imports", "LR"),
        ("class-hierarchy", class_edges(mods)[0], "inherits", "BT"),
    ]:
        edges, note = fit(edges, args.max_nodes)
        if not edges:
            print(f"{name}: no edges, skipped")
            continue
        dot_src = to_dot(edges, verb, direction)
        if args.format == "svg":
            svg = render_svg(dot_src)
            if svg is None:
                print("Graphviz `dot` not found; install graphviz or use --format mermaid", file=sys.stderr)
                return 1
            (args.out / f"{name}.svg").write_bytes(svg)
        elif args.format == "dot":
            (args.out / f"{name}.dot").write_text(dot_src, encoding="utf-8")
        else:
            (args.out / f"{name}.mmd").write_text(to_mermaid(edges, verb, direction), encoding="utf-8")
        print(f"{name}: {len({n for e in edges for n in e})} nodes, {len(edges)} edges" + (f" — {note}" if note else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
