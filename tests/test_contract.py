"""The data contract: which input files are accepted, and why others are not."""

from pathlib import Path

import pytest

from data_product.contract import (
    Column,
    Contract,
    ContractError,
    describe_read_error,
    validate,
)

from .conftest import CsvWriter

CONTRACT = Contract(
    columns=(
        Column("product_id", "BIGINT", nullable=False),
        Column("name", "VARCHAR", nullable=False),
        Column("registered_on", "DATE"),
        Column("units", "BIGINT"),
    )
)

VALID = """\
product_id,name,registered_on,units
1,Paracetamol 500 mg,2024-01-15,20
2,"Ácido fólico, 1 mg",,
"""


def violations_of(source: Path, contract: Contract = CONTRACT) -> list[str]:
    with pytest.raises(ContractError) as excinfo:
        validate(source, contract)
    return excinfo.value.violations


def test_valid_file_passes(write_csv: CsvWriter) -> None:
    validate(write_csv(VALID), CONTRACT)


def test_missing_column_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv("product_id,name,registered_on\n1,Paracetamol,2024-01-15\n")

    assert violations_of(source) == ["missing column 'units'"]


def test_unexpected_column_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv(
        "product_id,name,registered_on,units,price\n1,Paracetamol,2024-01-15,20,9.5\n"
    )

    assert violations_of(source) == ["unexpected column 'price'"]


def test_repeated_column_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv("product_id,name,name,registered_on,units\n1,a,b,2024-01-15,2\n")

    assert violations_of(source) == ["column 'name' appears 2 times in the header"]


def test_wrong_type_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv(
        "product_id,name,registered_on,units\n"
        "1,Paracetamol,2024-01-15,twenty\n"
        "2,Ibuprofeno,15/01/2024,10\n"
    )

    assert violations_of(source) == [
        "column 'registered_on': 1 value is not DATE, for example '15/01/2024'",
        "column 'units': 1 value is not BIGINT, for example 'twenty'",
    ]


def test_null_in_required_column_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv(
        "product_id,name,registered_on,units\n"
        "1,,2024-01-15,20\n"
        '2,"  ",2024-01-16,10\n'
        "3,Ibuprofeno,2024-01-17,5\n"
    )

    assert violations_of(source) == [
        "column 'name': 2 empty values, but the column is required"
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "product_id,name,registered_on,units\n",
            "the file has 0 data rows, expected at least 1",
        ),
        ("", "the file is empty: it has no header row"),
    ],
    ids=["header only", "zero bytes"],
)
def test_empty_file_is_rejected(write_csv: CsvWriter, text: str, expected: str) -> None:
    assert violations_of(write_csv(text)) == [expected]


def test_utf8_bom_file_is_read(write_csv: CsvWriter) -> None:
    validate(write_csv(VALID, encoding="utf-8-sig"), CONTRACT)


@pytest.mark.parametrize(
    ("text", "line"),
    [(VALID, 3), ("product_id,name,registered_on,units,año\n1,a,,2,x\n", 1)],
    ids=["in a data row", "in the header"],
)
def test_non_utf8_file_is_rejected_naming_encoding(
    write_csv: CsvWriter, text: str, line: int
) -> None:
    source = write_csv(text, encoding="latin-1")

    assert violations_of(source) == [
        f"line {line} is not valid UTF-8; save the file as UTF-8 and try again"
    ]


def test_semicolon_separated_file_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv("product_id;name;registered_on;units\n1;Paracetamol;;20\n")

    assert violations_of(source) == [
        "missing column 'product_id'",
        "missing column 'name'",
        "missing column 'registered_on'",
        "missing column 'units'",
        "unexpected column 'product_id;name;registered_on;units'",
    ]


def test_windows_line_endings_are_read(write_csv: CsvWriter) -> None:
    validate(write_csv(VALID, newline="\r\n"), CONTRACT)


def test_columns_in_a_different_order_are_accepted(write_csv: CsvWriter) -> None:
    source = write_csv(
        "units,name,product_id,registered_on\n20,Paracetamol,1,2024-01-15\n"
    )

    validate(source, CONTRACT)


def test_row_with_wrong_number_of_fields_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv(
        "product_id,name,registered_on,units\n"
        "1,Paracetamol,2024-01-15,20\n"
        "2,Ibuprofeno,2024-01-16,10,extra\n"
    )

    assert violations_of(source) == ["line 3 has 5 fields, expected 4"]


def test_row_with_unclosed_quote_is_rejected(write_csv: CsvWriter) -> None:
    source = write_csv(
        'product_id,name,registered_on,units\n1,"Paracetamol,2024-01-15,20\n'
    )

    assert violations_of(source) == ["line 2 has a quote that is never closed"]


def test_unknown_read_error_keeps_the_original_message() -> None:
    # Safety net for reader errors nobody has seen yet: show them as they are.
    message = "Invalid Input Error: something new\nmore detail"

    assert describe_read_error(message) == (
        "the file could not be read as CSV: Invalid Input Error: something new"
    )


def test_all_violations_are_reported_together(write_csv: CsvWriter) -> None:
    source = write_csv(
        "product_id,name,registered_on,units\n,Paracetamol,yesterday,20\n"
    )

    assert violations_of(source) == [
        "column 'product_id': 1 empty value, but the column is required",
        "column 'registered_on': 1 value is not DATE, for example 'yesterday'",
    ]


def test_error_message_lists_every_violation(write_csv: CsvWriter) -> None:
    source = write_csv("product_id,name\n1,Paracetamol\n")

    with pytest.raises(ContractError) as excinfo:
        validate(source, CONTRACT)

    assert (
        str(excinfo.value) == "missing column 'registered_on'\nmissing column 'units'"
    )


def test_missing_source_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"no-such-file\.csv"):
        validate(tmp_path / "no-such-file.csv", CONTRACT)


def test_contract_needs_at_least_one_column() -> None:
    with pytest.raises(ValueError, match="at least one column"):
        Contract(columns=())


def test_contract_rejects_repeated_column_names() -> None:
    with pytest.raises(ValueError, match="'name' is declared 2 times"):
        Contract(columns=(Column("name", "VARCHAR"), Column("name", "VARCHAR")))


def test_column_rejects_malformed_type() -> None:
    with pytest.raises(ValueError, match="not a valid type name"):
        Column("units", "BIGINT); DROP TABLE x; --")
