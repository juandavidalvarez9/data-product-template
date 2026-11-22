# data-product-template

[![CI](https://github.com/juandavidalvarez9/data-product-template/actions/workflows/ci.yml/badge.svg)](https://github.com/juandavidalvarez9/data-product-template/actions/workflows/ci.yml)

<!-- One sentence: what this product does and for whom. -->

## Problem

<!-- Who uses this product, what they do today, and what changes for them. -->

Not written yet.

## Data

<!-- Where the data comes from, its license and how often it changes.
     The details go in docs/data-card.md. -->

The project still reads the sample files of the template, in `tests/data/`.
They are described in the [data card](docs/data-card.md).

## Quick start

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.12 or newer
if it is missing.

```console
uv sync
uv run poe check
uv run data-product run tests/data/products.csv out/products.parquet
```

The last command prints:

```text
Wrote 5 rows to out/products.parquet
```

## Example

<!-- Show one real use of the product with its real output. The tests run
     every line that starts with "$ " in a console block and compare what it
     prints with the lines under it. -->

When a file breaks the data contract, nothing is written and every problem is
listed:

```console
$ uv run data-product run tests/data/products_broken.csv out/broken.parquet
tests/data/products_broken.csv does not meet the contract:
- column 'name': 1 empty value, but the column is required
- column 'registered_on': 1 value is not DATE, for example '15/01/2024'
- column 'units': 1 value is not BIGINT, for example 'twenty'
```

## How it is tested

`uv run poe check` runs the format check, the linter, the type checker and the
tests, and fails if branch coverage is under 90%. CI runs it on Ubuntu and
Windows with Python 3.12, 3.13 and 3.14. Time and memory at two sizes are in
[docs/benchmarks.md](docs/benchmarks.md).

## Limits

<!-- What this product does not do, and where it can be wrong. -->

- Only comma-separated UTF-8 files are accepted.
- The figures in [docs/benchmarks.md](docs/benchmarks.md) come from the
  template until `uv run poe bench` runs in this project.

## License

The code is under the [MIT license](LICENSE). The data has its own terms,
described in the [data card](docs/data-card.md).
