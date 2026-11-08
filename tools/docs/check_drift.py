#!/usr/bin/env python3
"""Warn when code changes may have left the docs behind (document-it skill).

Checks, between a base ref and HEAD:
  1. Source files changed while nothing under docs/ (or README) changed.
  2. Public API breaking changes, via `griffe check` (if griffe is installed): removed or
     renamed objects, changed signatures — these almost always need doc updates.

Generated docs (API reference, diagrams) update themselves; this flags the hand-written pages.

Usage:
    python3 tools/docs/check_drift.py --base origin/main [--github] [--strict]

Exit code: 0 normally; 1 with --strict when drift is detected; 2 on usage/git errors.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

CODE_EXT = {".py", ".pyi", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".rb", ".cs"}
DOC_PREFIXES = ("docs/", "README", "zensical.toml", "mkdocs.yml", "CHANGELOG")
NON_SOURCE_DIRS = ("tests/", "test/", "docs/", "tools/", ".github/", "benchmarks/")
EXCLUDE_TOPS = {"tests", "test", "docs", "tools", "examples", "scripts", "benchmarks"}


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"git {' '.join(args)} failed")
    return out.stdout


def changed_files(base: str, head: str) -> list[str]:
    try:
        return [f for f in git("diff", "--name-only", f"{base}...{head}").splitlines() if f]
    except RuntimeError:
        # e.g. base is a commit without a merge-base relation (force push); use two-dot diff
        return [f for f in git("diff", "--name-only", base, head).splitlines() if f]


def source_root(root: Path) -> Path:
    src = root / "src"
    return src if src.is_dir() else root


def python_packages(src: Path) -> list[str]:
    return sorted(
        d.name for d in src.iterdir()
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in EXCLUDE_TOPS
    )


def griffe_breakages(packages: list[str], base: str, search: Path) -> list[str]:
    if importlib.util.find_spec("griffe") is None:
        return []
    lines: list[str] = []
    for pkg in packages:
        out = subprocess.run(
            # search path must be relative: griffe resolves it inside a worktree of the base ref
            [sys.executable, "-m", "griffe", "check", pkg, "--against", base, "--search", search.as_posix(), "--no-color"],
            capture_output=True, text=True,
        )
        text = (out.stdout + out.stderr).strip()
        if out.returncode != 0 and text:
            lines += [ln for ln in text.splitlines() if ln.strip()]
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/main", help="base ref to compare against (default: origin/main)")
    ap.add_argument("--head", default="HEAD", help="head ref (default: HEAD)")
    ap.add_argument("--src", action="append", help="source path prefix to watch (repeatable; default: src/ or package dirs)")
    ap.add_argument("--packages", default="", help="comma-separated Python packages for the API check (default: auto)")
    ap.add_argument("--no-api", action="store_true", help="skip the griffe public-API check")
    ap.add_argument("--github", action="store_true", help="emit GitHub Actions annotations and a step summary")
    ap.add_argument("--strict", action="store_true", help="exit 1 when drift is detected")
    args = ap.parse_args()

    try:
        root = Path(git("rev-parse", "--show-toplevel").strip())
        os.chdir(root)
        files = changed_files(args.base, args.head)
    except RuntimeError as e:
        print(f"check_drift: {e}", file=sys.stderr)
        return 2

    src = source_root(root)
    pkgs = [p for p in args.packages.split(",") if p] or python_packages(src)
    watch = args.src or ([f"{src.relative_to(root).as_posix()}/"] if src != root else [f"{p}/" for p in pkgs])
    if not watch:
        watch = [""]  # no layout detected: any code file outside non-source dirs counts

    code_changed = [
        f for f in files
        if Path(f).suffix in CODE_EXT and any(f.startswith(w) for w in watch) and not f.startswith(NON_SOURCE_DIRS)
    ]
    docs_changed = [f for f in files if f.startswith(DOC_PREFIXES)]
    api_breaks = [] if args.no_api or not pkgs else griffe_breakages(pkgs, args.base, src.relative_to(root))

    report = ["## Docs drift check", "", f"Compared `{args.base}`...`{args.head}`: {len(files)} files changed."]
    drift = False
    if code_changed and not docs_changed:
        drift = True
        report += ["", f"**{len(code_changed)} source file(s) changed with no documentation changes:**", ""]
        report += [f"- `{f}`" for f in code_changed[:50]]
        if args.github:
            for f in code_changed[:20]:
                print(f"::warning file={f},title=Docs may need updating::Source changed but no files under docs/ or README changed.")
    elif code_changed:
        report += ["", f"Source changed ({len(code_changed)} files) and docs changed ({len(docs_changed)} files). ✔"]
    else:
        report += ["", "No source changes. ✔"]

    if api_breaks:
        drift = True
        report += ["", "**Public API breaking changes (griffe) — update docs that mention these:**", "", "```text", *api_breaks[:100], "```"]
        if args.github:
            for ln in api_breaks[:20]:
                print(f"::warning title=Public API changed::{ln}")
    elif not args.no_api and pkgs and importlib.util.find_spec("griffe") is None:
        report += ["", "_griffe not installed — public API check skipped._"]

    if drift:
        report += ["", "Generated API reference and diagrams update automatically; review tutorials, how-to guides, "
                   "explanation pages, and README for anything these changes affect. If no docs change is needed, "
                   "add the `docs-not-needed` label."]

    text = "\n".join(report)
    print(text)
    if args.github and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 1 if (drift and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
