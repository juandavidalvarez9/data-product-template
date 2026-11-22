"""Data contract for input files.

A contract says which columns a CSV file must have, the type of each one and
whether it may be empty. `validate` checks a file against a contract and
reports every problem it finds, so whoever fixes the file sees them all at once.
"""

import csv
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb

_TYPE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_ ]*(\(\d+(, ?\d+)?\))?")
_ERROR_LINE = re.compile(r"CSV Error on Line: (\d+)")
_FIELD_COUNT = re.compile(r"Expected Number of Columns: (\d+) Found: (\d+)")


@dataclass(frozen=True)
class Column:
    """One input column: its name, its DuckDB type and whether it may be empty."""

    name: str
    dtype: str
    nullable: bool = True

    def __post_init__(self) -> None:
        if not _TYPE_NAME.fullmatch(self.dtype):
            raise ValueError(f"{self.dtype!r} is not a valid type name")


@dataclass(frozen=True)
class Contract:
    """The columns an input file must have and how many rows it needs."""

    columns: tuple[Column, ...]
    min_rows: int = 1

    def __post_init__(self) -> None:
        if not self.columns:
            raise ValueError("a contract needs at least one column")
        for name, times in Counter(column.name for column in self.columns).items():
            if times > 1:
                raise ValueError(f"column {name!r} is declared {times} times")


class ContractError(Exception):
    """The input file does not meet the contract."""

    def __init__(self, violations: Sequence[str]) -> None:
        self.violations = list(violations)
        super().__init__("\n".join(self.violations))


def validate(source: Path, contract: Contract) -> None:
    """Raise `ContractError` if the CSV file at `source` breaks the contract."""
    if not source.is_file():
        raise FileNotFoundError(f"source file not found: {source}")

    try:
        header = read_header(source)
    except UnicodeDecodeError:
        raise ContractError([_not_utf8(line=1)]) from None
    if not header:
        raise ContractError(["the file is empty: it has no header row"])

    violations = _header_violations(header, contract)
    if not violations:
        violations = _row_violations(source, header, contract)
    if violations:
        raise ContractError(violations)


def read_header(source: Path) -> list[str]:
    """Return the column names in the first line of a UTF-8 CSV file."""
    with source.open("rb") as handle:
        first_line = handle.readline()
    return next(csv.reader([first_line.decode("utf-8-sig")]), [])


def read_csv_sql(source: Path, header: Sequence[str]) -> str:
    """Return the SQL table expression that reads the CSV file at `source`.

    Every column is read as text. The reader gets the exact column names
    instead of guessing them: when it guesses, a row with the wrong number of
    fields can make it skip lines without saying so.
    """
    columns = ", ".join(f"{quote_text(name)}: 'VARCHAR'" for name in header)
    return (
        f"read_csv({quote_text(str(source))}, header = true, auto_detect = false, "
        f"columns = {{{columns}}}, delim = ',', quote = '\"', escape = '\"')"
    )


def quote_name(name: str) -> str:
    """Quote a column name for use in SQL."""
    return '"' + name.replace('"', '""') + '"'


def quote_text(text: str) -> str:
    """Quote a text value for use in SQL."""
    return "'" + text.replace("'", "''") + "'"


def _header_violations(header: Sequence[str], contract: Contract) -> list[str]:
    expected = [column.name for column in contract.columns]
    found = Counter(header)
    return (
        [f"missing column {name!r}" for name in expected if name not in found]
        + [f"unexpected column {name!r}" for name in found if name not in expected]
        + [
            f"column {name!r} appears {times} times in the header"
            for name, times in found.items()
            if times > 1
        ]
    )


def _row_violations(
    source: Path, header: Sequence[str], contract: Contract
) -> list[str]:
    """Check every row in a single pass over the file."""
    selections = ["count(*)"]
    for column in contract.columns:
        name = quote_name(column.name)
        empty = f"({name} IS NULL OR trim({name}) = '')"
        wrong_type = f"(NOT {empty} AND TRY_CAST({name} AS {column.dtype}) IS NULL)"
        selections += [
            f"count(*) FILTER (WHERE {empty})",
            f"count(*) FILTER (WHERE {wrong_type})",
            f"min({name}) FILTER (WHERE {wrong_type})",
        ]
    query = f"SELECT {', '.join(selections)} FROM {read_csv_sql(source, header)}"

    try:
        with duckdb.connect() as connection:
            ((rows, *checks),) = connection.execute(query).fetchall()
    except duckdb.InvalidInputException as error:
        return [describe_read_error(str(error))]

    violations = []
    if rows < contract.min_rows:
        violations.append(
            f"the file has {rows} data rows, expected at least {contract.min_rows}"
        )
    for position, column in enumerate(contract.columns):
        empty_count, wrong_count, example = checks[3 * position : 3 * position + 3]
        if empty_count and not column.nullable:
            violations.append(
                f"column {column.name!r}: {_count(empty_count, 'empty value')}, "
                "but the column is required"
            )
        if wrong_count:
            verb = "is" if wrong_count == 1 else "are"
            violations.append(
                f"column {column.name!r}: {_count(wrong_count, 'value')} {verb} "
                f"not {column.dtype}, for example {example!r}"
            )
    return violations


def describe_read_error(message: str) -> str:
    """Turn a DuckDB CSV error into one line a person can act on."""
    line = _ERROR_LINE.search(message)
    fields = _FIELD_COUNT.search(message)
    if line and fields:
        expected, found = fields.groups()
        return f"line {line.group(1)} has {found} fields, expected {expected}"
    if line and "Invalid unicode" in message:
        return _not_utf8(line=int(line.group(1)))
    if line and "unterminated quote" in message:
        return f"line {line.group(1)} has a quote that is never closed"
    return f"the file could not be read as CSV: {message.splitlines()[0]}"


def _not_utf8(line: int) -> str:
    return f"line {line} is not valid UTF-8; save the file as UTF-8 and try again"


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"
