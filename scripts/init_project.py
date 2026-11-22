"""Turn a copy of this template into a new product.

    uv run python scripts/init_project.py river-levels --command rivers

The script renames the Python package, the distribution and the command
everywhere they appear. It replaces the README with a product README to fill
in and starts a new changelog. Then it deletes the files only the template
needs, itself included. Run it once, on a fresh copy of the template.

It checks everything before it writes anything. If a name is not valid, or
the project was already initialized, it stops and changes no file.
"""

import argparse
import keyword
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

TEMPLATE_PACKAGE = "data_product"
TEMPLATE_DIST = "data-product"
TEMPLATE_REPO = "data-product-template"
PRODUCT_README = Path("scripts") / "product_readme.md"
TEMPLATE_ONLY = (
    Path("scripts") / "init_project.py",
    Path("tests") / "test_init_project.py",
    PRODUCT_README,
)
NEW_CHANGELOG = """\
# Changelog

All notable changes to this project are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project started from the data product template.
"""
SKIPPED_FOLDERS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "out",
        "dist",
        "build",
    }
)

_HYPHENATED = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")

# Stand-ins used while rewriting, so a new name that contains one of the
# template's names is not rewritten a second time.
_DIST, _COMMAND, _PACKAGE = "\0dist\0", "\0command\0", "\0package\0"


class InitError(Exception):
    """The project cannot be initialized as asked. No file was changed."""


def init_project(
    root: Path, package: str, dist_name: str, command: str | None = None
) -> None:
    """Rename the template at `root` to a new product.

    `dist_name` is the name in pyproject.toml, `package` is the name used in
    `import`, and `command` is what a person types in the terminal. The
    command is the distribution name unless another one is given.
    """
    command = dist_name if command is None else command
    _check_names(package, dist_name, command)
    _check_project(root, package)

    rewritten = _rewrite(root, package, dist_name, command)
    readme = (root / PRODUCT_README).read_bytes().decode("utf-8")
    rewritten[root / "README.md"] = _rename(readme, package, dist_name, command)
    rewritten[root / "CHANGELOG.md"] = NEW_CHANGELOG

    for path, text in rewritten.items():
        path.write_bytes(text.encode("utf-8"))
    (root / "src" / TEMPLATE_PACKAGE).rename(root / "src" / package)
    for relative in TEMPLATE_ONLY:
        (root / relative).unlink(missing_ok=True)
    _format(root)


def _format(root: Path) -> None:
    """Put the renamed code back in the standard format.

    A longer name can push a line over the length limit. If ruff is not
    installed for this Python, nothing happens here and `uv run poe check`
    will ask for `uv run poe format`.
    """
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--quiet", str(root)],
        capture_output=True,
        check=False,
    )


def _check_names(package: str, dist_name: str, command: str) -> None:
    for name in (dist_name, command):
        if not _HYPHENATED.fullmatch(name):
            raise InitError(
                f"{name!r} is not a valid name: use lowercase letters, digits "
                "and hyphens, and start with a letter"
            )
    if not package.isidentifier() or package != package.lower():
        raise InitError(
            f"{package!r} is not a valid Python package name: use lowercase "
            "letters, digits and underscores"
        )
    if keyword.iskeyword(package):
        raise InitError(f"{package!r} is a Python keyword")
    if package in sys.stdlib_module_names:
        raise InitError(f"{package!r} is a module of the standard library")
    for name, template_name in (
        (package, TEMPLATE_PACKAGE),
        (dist_name, TEMPLATE_DIST),
    ):
        if name == template_name:
            raise InitError(f"{name!r} is the template's own name")


def _check_project(root: Path, package: str) -> None:
    if not (root / "src" / TEMPLATE_PACKAGE).is_dir():
        raise InitError(
            f"{root} has already been initialized, or it is not a copy of the "
            f"template: src/{TEMPLATE_PACKAGE} is missing"
        )
    if (root / "src" / package).exists():
        raise InitError(f"src/{package} already exists")
    if not (root / PRODUCT_README).is_file():
        raise InitError(
            f"{PRODUCT_README.as_posix()} is missing: it becomes the README of "
            "the new product"
        )


def _rewrite(root: Path, package: str, dist_name: str, command: str) -> dict[Path, str]:
    """Return the new text of every file that mentions the template's names."""
    texts = _read_text_files(root)

    # In these three places the name is the distribution, not the command.
    distribution_only = (
        (Path("pyproject.toml"), f'name = "{TEMPLATE_DIST}"', f'name = "{_DIST}"'),
        (Path("uv.lock"), f'name = "{TEMPLATE_DIST}"', f'name = "{_DIST}"'),
        (
            Path("src") / TEMPLATE_PACKAGE / "__init__.py",
            f'version("{TEMPLATE_DIST}")',
            f'version("{_DIST}")',
        ),
    )
    for relative, old, new in distribution_only:
        text = texts.get(root / relative, "")
        if text.count(old) != 1:
            raise InitError(
                f"expected {old!r} exactly once in {relative}: the template "
                "changed, so scripts/init_project.py must change with it"
            )
        texts[root / relative] = text.replace(old, new)

    rewritten = {}
    for path, text in texts.items():
        new_text = _rename(text, package, dist_name, command)
        if new_text != path.read_bytes().decode("utf-8"):
            rewritten[path] = new_text
    return rewritten


def _rename(text: str, package: str, dist_name: str, command: str) -> str:
    """Replace the template's names in `text`.

    The repository name becomes the distribution name, the distribution name
    becomes the command (the three places where it is the distribution were
    marked before this runs) and the package name becomes the new package.
    """
    return (
        text.replace(TEMPLATE_REPO, _DIST)
        .replace(TEMPLATE_DIST, _COMMAND)
        .replace(TEMPLATE_PACKAGE, _PACKAGE)
        .replace(_DIST, dist_name)
        .replace(_COMMAND, command)
        .replace(_PACKAGE, package)
    )


def _read_text_files(root: Path) -> dict[Path, str]:
    template_only = {root / relative for relative in TEMPLATE_ONLY}
    texts = {}
    for path in sorted(root.rglob("*")):
        inside = path.relative_to(root).parts
        if not path.is_file() or path in template_only:
            continue
        if SKIPPED_FOLDERS.intersection(inside):
            continue
        try:
            texts[path] = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue  # not a text file
    return texts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="distribution name, for example river-levels")
    parser.add_argument(
        "--package",
        help="Python package name (default: the name with underscores)",
    )
    parser.add_argument(
        "--command",
        help="name of the command-line program (default: the name)",
    )
    args = parser.parse_args(argv)

    package = args.package or args.name.replace("-", "_")
    command = args.command or args.name
    root = Path(__file__).resolve().parents[1]
    try:
        init_project(root, package=package, dist_name=args.name, command=command)
    except InitError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        f"Renamed the template to {args.name} "
        f"(package {package}, command {command}).\n"
        "Next steps:\n"
        "  uv sync\n"
        "  uv run poe check    (if it asks for it: uv run poe format)\n"
        "  fill in README.md and docs/data-card.md for your product\n"
        "  commit the result"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
