"""The documentation says what the code does.

These tests run the commands the README shows and compare their output with
what the README prints. One command is left out on purpose: `uv run poe check`.
CI runs exactly that command, and running it here would start this test suite
again from inside itself.
"""

import datetime
import re
import shlex
import subprocess
import tomllib
from pathlib import Path

import pytest

from data_product.pipeline import EXAMPLE_CONTRACT

from .conftest import NOT_PART_OF_A_COPY, ROOT, copy_project, run_uv

README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"
DATA_CARD = ROOT / "docs" / "data-card.md"
CHECK = "uv run poe check"
# The template keeps the product README here; it becomes README.md.
PRODUCT_README = ROOT / "scripts" / "product_readme.md"
LINK = re.compile(r"\]\(([^)\s]+)\)")
RELEASE_HEADING = re.compile(r"^## \[([^\]]+)\](?: - (\S+))?$", re.MULTILINE)


def section(markdown: str, title: str) -> str:
    """Return the text under a `## title` heading, up to the next one."""
    match = re.search(
        rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"no '## {title}' section"
    return match.group(1)


def code_blocks(markdown: str, language: str) -> list[str]:
    return re.findall(rf"^```{language}\n(.*?)^```", markdown, re.MULTILINE | re.DOTALL)


def console_examples(markdown: str) -> list[tuple[str, list[str]]]:
    """Return each `$ command` shown in the README with the output under it."""
    examples: list[tuple[str, list[str]]] = []
    for block in code_blocks(markdown, "console"):
        output: list[str] | None = None  # output belongs to the `$` line above it
        for line in block.splitlines():
            if line.startswith("$ "):
                output = []
                examples.append((line.removeprefix("$ "), output))
            elif output is not None:
                output.append(line)
    return examples


def without_comments(markdown: str) -> str:
    return re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)


def markdown_files() -> list[Path]:
    ignored = NOT_PART_OF_A_COPY(str(ROOT), [])
    return [
        path
        for path in sorted(ROOT.rglob("*.md"))
        if not set(path.relative_to(ROOT).parts) & set(ignored)
        and ".venv" not in path.parts
    ]


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A fresh copy of this project with its dependencies installed."""
    root = copy_project(tmp_path_factory.mktemp("docs") / "project")
    sync = run_uv(root, "sync", "--locked")
    assert sync.returncode == 0, sync.stderr
    return root


def run_readme_command(project: Path, command: str) -> subprocess.CompletedProcess[str]:
    words = shlex.split(command)
    assert words[0] == "uv", f"README commands should start with uv: {command!r}"
    return run_uv(project, *words[1:])


def lines_of(output: str) -> list[str]:
    # Windows prints paths with backslashes; the README shows forward slashes.
    return output.replace("\\", "/").splitlines()


def test_quickstart_commands_run(project: Path) -> None:
    quick_start = section(README.read_text(encoding="utf-8"), "Quick start")
    (block,) = code_blocks(quick_start, "console")
    commands = [line for line in block.splitlines() if line.strip()]
    lock_before = (project / "uv.lock").read_bytes()

    assert CHECK in commands
    result = None
    for command in commands:
        if command == CHECK:
            continue
        result = run_readme_command(project, command)
        assert result.returncode == 0, f"{command}\n{result.stderr}"

    (expected,) = code_blocks(quick_start, "text")
    assert result is not None
    assert lines_of(result.stdout) == expected.splitlines()
    assert (project / "uv.lock").read_bytes() == lock_before


def test_readme_examples_show_real_output(project: Path) -> None:
    examples = console_examples(README.read_text(encoding="utf-8"))

    assert examples, "the README should show at least one command with its output"
    for command, expected in examples:
        result = run_readme_command(project, command)
        assert lines_of(result.stdout + result.stderr) == expected, command


def test_readme_states_its_limits() -> None:
    limits = without_comments(section(README.read_text(encoding="utf-8"), "Limits"))

    assert [line for line in limits.splitlines() if line.startswith("- ")]


@pytest.mark.parametrize(
    "document", markdown_files(), ids=lambda path: str(path.relative_to(ROOT))
)
def test_relative_links_point_to_existing_files(document: Path) -> None:
    # A file that becomes README.md is read from where it will be.
    base = ROOT if document == PRODUCT_README else document.parent
    targets = LINK.findall(document.read_text(encoding="utf-8"))

    broken = [
        target
        for target in targets
        if not target.startswith(("http://", "https://", "#", "mailto:"))
        and not (base / target.split("#")[0]).exists()
    ]

    assert broken == []


def test_data_card_lists_every_contract_column() -> None:
    fields = section(DATA_CARD.read_text(encoding="utf-8"), "Fields")
    rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in fields.splitlines()
        if line.startswith("| `")
    ]

    assert [
        (name.strip("`"), dtype, required) for name, dtype, required, _ in rows
    ] == [
        (column.name, column.dtype, "no" if column.nullable else "yes")
        for column in EXAMPLE_CONTRACT.columns
    ]


def test_changelog_releases_match_the_version() -> None:
    changelog = CHANGELOG.read_text(encoding="utf-8")
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    (unreleased, *releases) = RELEASE_HEADING.findall(changelog)

    assert unreleased == ("Unreleased", ""), "the first section must be [Unreleased]"
    for version, date in releases:
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
        datetime.date.fromisoformat(date)
        assert f"\n[{version}]: https://" in changelog, f"no link for [{version}]"
    numbers = [tuple(map(int, version.split("."))) for version, _ in releases]
    assert numbers == sorted(numbers, reverse=True), "newest release first"
    dates = [date for _, date in releases]
    assert dates == sorted(dates, reverse=True), "newest date first"
    if releases:
        newest, _ = releases[0]
        assert newest == pyproject["project"]["version"]
