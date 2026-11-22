"""Command-line entry point."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from data_product import __version__
from data_product.contract import ContractError
from data_product.pipeline import EXAMPLE_CONTRACT, run

PROG = "data-product"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Starting point for small, tested data products.",
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")

    commands = parser.add_subparsers(dest="command", title="commands")
    run_parser = commands.add_parser(
        "run",
        help="check a CSV file and write it as Parquet",
        description="Check a CSV file against the contract and write it as Parquet.",
    )
    run_parser.add_argument("source", type=Path, help="CSV file to read")
    run_parser.add_argument("dest", type=Path, help="Parquet file to write")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the process exit code.

    0 means success, 1 means the input was rejected, and argparse exits with 2
    when the command itself is wrong. A bare call prints the help text.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return _run(args.source, args.dest)


def _run(source: Path, dest: Path) -> int:
    try:
        report = run(source, dest, EXAMPLE_CONTRACT)
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1
    except ContractError as error:
        print(f"{source} does not meet the contract:", file=sys.stderr)
        for violation in error.violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print(f"Wrote {report.rows_out} rows to {report.output}")
    return 0
