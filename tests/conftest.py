"""Helpers shared by the tests."""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOT_PART_OF_A_COPY = shutil.ignore_patterns(
    ".git", ".venv", "__pycache__", ".*_cache", ".coverage*", "out", "dist", "build"
)

CsvWriter = Callable[..., Path]


@pytest.fixture
def write_csv(tmp_path: Path) -> CsvWriter:
    """Return a function that writes a small CSV file and returns its path."""

    def write(
        text: str,
        *,
        name: str = "input.csv",
        encoding: str = "utf-8",
        newline: str = "\n",
    ) -> Path:
        path = tmp_path / name
        path.write_bytes(text.replace("\n", newline).encode(encoding))
        return path

    return write


def copy_project(destination: Path) -> Path:
    """Copy this project to `destination`, as a person would get it from git."""
    shutil.copytree(ROOT, destination, ignore=NOT_PART_OF_A_COPY)
    return destination


def run_uv(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run uv in `project` without leaking this test run's settings.

    `--quiet` silences uv's own messages. The program it runs keeps its output.
    """
    uv = shutil.which("uv")
    assert uv is not None, "uv must be on PATH for this test"
    leaked = ("COVERAGE_", "COV_CORE_", "VIRTUAL_ENV", "PYTEST_")
    env = {k: v for k, v in os.environ.items() if not k.startswith(leaked)}
    return subprocess.run(
        [uv, "--quiet", *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
