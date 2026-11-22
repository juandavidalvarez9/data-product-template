"""The version is declared once, in pyproject.toml, and the package reports it."""

import tomllib
from pathlib import Path

import data_product

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_version_matches_metadata() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert data_product.__version__ == pyproject["project"]["version"]
