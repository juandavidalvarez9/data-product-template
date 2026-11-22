"""The command line: what a person sees when they type `data-product`."""

import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest

import data_product
from data_product.cli import main

from .conftest import CsvWriter

SAMPLE = Path(__file__).parent / "data" / "products.csv"
BROKEN_SAMPLE = Path(__file__).parent / "data" / "products_broken.csv"


def test_cli_version_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"data-product {data_product.__version__}"


def test_cli_unknown_command_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["no-such-command"])

    assert excinfo.value.code == 2
    assert "no-such-command" in capsys.readouterr().err


def test_cli_without_arguments_prints_help_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])

    assert exit_code == 0
    assert "usage: data-product" in capsys.readouterr().out


def test_console_script_points_to_main() -> None:
    (script,) = entry_points(group="console_scripts", name="data-product")

    assert script.load() is main


def test_module_runs_as_script() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "data_product", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"data-product {data_product.__version__}"


def test_cli_run_writes_output_and_reports_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "products.parquet"

    exit_code = main(["run", str(SAMPLE), str(dest)])

    assert exit_code == 0
    assert dest.is_file()
    assert capsys.readouterr().out.strip() == f"Wrote 5 rows to {dest}"


def test_cli_run_prints_violations_and_exits_1(
    write_csv: CsvWriter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write_csv("product_id,name\n1,Paracetamol\n")
    dest = tmp_path / "products.parquet"

    exit_code = main(["run", str(source), str(dest)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.splitlines() == [
        f"{source} does not meet the contract:",
        "- missing column 'registered_on'",
        "- missing column 'units'",
    ]
    assert not dest.exists()


def test_cli_run_missing_source_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "no-such-file.csv"

    exit_code = main(["run", str(source), str(tmp_path / "products.parquet")])

    assert exit_code == 1
    assert capsys.readouterr().err.strip() == f"source file not found: {source}"


def test_cli_run_without_paths_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["run"])

    assert excinfo.value.code == 2
    assert "source" in capsys.readouterr().err


def test_broken_sample_lists_every_problem(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The README shows this exact output.
    exit_code = main(["run", str(BROKEN_SAMPLE), str(tmp_path / "products.parquet")])

    assert exit_code == 1
    assert capsys.readouterr().err.splitlines()[1:] == [
        "- column 'name': 1 empty value, but the column is required",
        "- column 'registered_on': 1 value is not DATE, for example '15/01/2024'",
        "- column 'units': 1 value is not BIGINT, for example 'twenty'",
    ]
