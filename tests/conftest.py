"""Helpers shared by the tests."""

from collections.abc import Callable
from pathlib import Path

import pytest

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
