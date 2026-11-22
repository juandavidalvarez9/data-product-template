"""Command-line entry point."""

import argparse
from collections.abc import Sequence

from data_product import __version__

PROG = "data-product"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Starting point for small, tested data products.",
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the process exit code.

    There are no subcommands yet, so a bare call prints the help text.
    """
    parser = build_parser()
    parser.parse_known_args(argv)
    parser.print_help()
    return 0
