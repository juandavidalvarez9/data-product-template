"""The sample pipeline: a checked CSV file in, a typed Parquet file out."""

import datetime
from pathlib import Path

import duckdb
import pytest

from data_product.contract import ContractError
from data_product.pipeline import EXAMPLE_CONTRACT, RunReport, run

from .conftest import CsvWriter

SAMPLE = Path(__file__).parent / "data" / "products.csv"

VALID = """\
product_id,name,registered_on,units
1,Paracetamol 500 mg,2024-01-15,20
2,"Ácido fólico, 1 mg",,
"""


def read_parquet(path: Path) -> list[tuple[object, ...]]:
    with duckdb.connect() as connection:
        return connection.execute(
            "SELECT * FROM read_parquet(?) ORDER BY product_id", [str(path)]
        ).fetchall()


def column_types(path: Path) -> dict[str, str]:
    with duckdb.connect() as connection:
        described = connection.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]
        ).fetchall()
    return {name: dtype for name, dtype, *_ in described}


def test_run_writes_typed_parquet(write_csv: CsvWriter, tmp_path: Path) -> None:
    dest = tmp_path / "products.parquet"

    report = run(write_csv(VALID), dest, EXAMPLE_CONTRACT)

    assert report == RunReport(rows_in=2, rows_out=2, output=dest)
    assert column_types(dest) == {
        "product_id": "BIGINT",
        "name": "VARCHAR",
        "registered_on": "DATE",
        "units": "BIGINT",
    }
    assert read_parquet(dest) == [
        (1, "Paracetamol 500 mg", datetime.date(2024, 1, 15), 20),
        (2, "Ácido fólico, 1 mg", None, None),
    ]


def test_run_reads_file_with_byte_order_mark(
    write_csv: CsvWriter, tmp_path: Path
) -> None:
    dest = tmp_path / "products.parquet"

    run(write_csv(VALID, encoding="utf-8-sig"), dest, EXAMPLE_CONTRACT)

    assert [row[0] for row in read_parquet(dest)] == [1, 2]
    assert "product_id" in column_types(dest)


def test_blank_text_becomes_null(write_csv: CsvWriter, tmp_path: Path) -> None:
    source = write_csv('product_id,name,registered_on,units\n1,Paracetamol,"  ","  "\n')
    dest = tmp_path / "products.parquet"

    run(source, dest, EXAMPLE_CONTRACT)

    assert read_parquet(dest) == [(1, "Paracetamol", None, None)]


def test_output_columns_follow_the_contract_order(
    write_csv: CsvWriter, tmp_path: Path
) -> None:
    source = write_csv("units,name,product_id,registered_on\n20,Paracetamol,1,\n")
    dest = tmp_path / "products.parquet"

    run(source, dest, EXAMPLE_CONTRACT)

    assert list(column_types(dest)) == ["product_id", "name", "registered_on", "units"]
    assert read_parquet(dest) == [(1, "Paracetamol", None, 20)]


def test_run_creates_missing_output_folder(
    write_csv: CsvWriter, tmp_path: Path
) -> None:
    dest = tmp_path / "out" / "nested" / "products.parquet"

    run(write_csv(VALID), dest, EXAMPLE_CONTRACT)

    assert dest.is_file()


def test_failed_run_leaves_no_partial_output(
    write_csv: CsvWriter, tmp_path: Path
) -> None:
    out_dir = tmp_path / "out"
    bad_source = write_csv("product_id,name,registered_on,units\n1,,,\n")

    with pytest.raises(ContractError):
        run(bad_source, out_dir / "products.parquet", EXAMPLE_CONTRACT)

    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def test_failed_write_keeps_previous_output(
    write_csv: CsvWriter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "out" / "products.parquet"
    dest.parent.mkdir()
    dest.write_bytes(b"previous run")

    def disk_full(*_: object) -> None:
        raise OSError("No space left on device")

    monkeypatch.setattr(Path, "replace", disk_full)

    with pytest.raises(OSError, match="No space left"):
        run(write_csv(VALID), dest, EXAMPLE_CONTRACT)

    assert dest.read_bytes() == b"previous run"
    assert [path.name for path in dest.parent.iterdir()] == ["products.parquet"]


def test_rerun_is_idempotent(write_csv: CsvWriter, tmp_path: Path) -> None:
    source = write_csv(VALID)
    dest = tmp_path / "products.parquet"

    first = run(source, dest, EXAMPLE_CONTRACT)
    rows_after_first = read_parquet(dest)
    second = run(source, dest, EXAMPLE_CONTRACT)

    assert second == first
    assert read_parquet(dest) == rows_after_first
    assert [path.name for path in tmp_path.iterdir() if path != source] == [
        "products.parquet"
    ]


def test_sample_data_meets_the_example_contract(tmp_path: Path) -> None:
    report = run(SAMPLE, tmp_path / "products.parquet", EXAMPLE_CONTRACT)

    assert (report.rows_in, report.rows_out) == (5, 5)
