"""Sample pipeline: check a CSV file against a contract, then write it as Parquet.

Replace `EXAMPLE_CONTRACT` and the query in `run` with your product's own.
Keep the two guarantees the tests pin down: nothing is written unless the
input meets the contract, and a failed run never leaves a partial output file.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb

from data_product.contract import (
    Column,
    Contract,
    quote_name,
    quote_text,
    read_csv_sql,
    read_header,
    validate,
)

EXAMPLE_CONTRACT = Contract(
    columns=(
        Column("product_id", "BIGINT", nullable=False),
        Column("name", "VARCHAR", nullable=False),
        Column("registered_on", "DATE"),
        Column("units", "BIGINT"),
    )
)


@dataclass(frozen=True)
class RunReport:
    """What a run read and what it wrote.

    The sample pipeline writes every row it reads, so both counts are equal.
    A product that filters or joins rows reports them separately.
    """

    rows_in: int
    rows_out: int
    output: Path


def run(source: Path, dest: Path, contract: Contract) -> RunReport:
    """Validate the CSV file at `source` and write it to `dest` as Parquet.

    The output has the contract's columns, in the contract's order and with
    the contract's types. It is written under a temporary name and renamed at
    the end, so `dest` is either the previous file or the complete new one.
    """
    validate(source, contract)

    columns = ", ".join(_typed(column) for column in contract.columns)
    table = read_csv_sql(source, read_header(source))
    partial = dest.with_name(dest.name + ".partial")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with duckdb.connect() as connection:
            ((rows,),) = connection.execute(
                f"COPY (SELECT {columns} FROM {table}) "
                f"TO {quote_text(str(partial))} (FORMAT parquet)"
            ).fetchall()
        partial.replace(dest)
    finally:
        partial.unlink(missing_ok=True)
    return RunReport(rows_in=rows, rows_out=rows, output=dest)


def _typed(column: Column) -> str:
    """SQL that converts one text column to its contract type; blank is NULL."""
    name = quote_name(column.name)
    return (
        f"CAST(CASE WHEN trim({name}) = '' THEN NULL ELSE {name} END "
        f"AS {column.dtype}) AS {name}"
    )
