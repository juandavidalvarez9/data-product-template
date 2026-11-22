"""The command line: what a person sees when they type `data-product`."""

import subprocess
import sys
from importlib.metadata import entry_points

import pytest

import data_product
from data_product.cli import main


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
