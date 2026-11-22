# data-product-template

Starting point for small, tested data products: one Python package, one
command line, and one command that runs every check.

> **Status:** early. The template is being built in small pull requests.
> Today it has the package skeleton, the checks, CI, a sample pipeline and
> scale measurements. A script to start a new product arrives next.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.12 or newer (uv installs it for you if it is missing)

## Quick start

```console
uv sync
uv run poe check
uv run data-product run tests/data/products.csv out/products.parquet
```

`uv sync` creates the virtual environment and installs the exact dependency
versions pinned in `uv.lock`. The last command prints:

```text
Wrote 5 rows to out/products.parquet
```

## Sample pipeline

The template ships one small pipeline, so a new product starts from code that
already works. It checks a CSV file against a **data contract** and writes it
as Parquet.

The contract lives in `src/data_product/pipeline.py`. It lists the columns the
file must have, the type of each one and which ones may be empty:

```python
EXAMPLE_CONTRACT = Contract(
    columns=(
        Column("product_id", "BIGINT", nullable=False),
        Column("name", "VARCHAR", nullable=False),
        Column("registered_on", "DATE"),
        Column("units", "BIGINT"),
    )
)
```

When a file breaks the contract, nothing is written and every problem is
listed at once:

```console
$ uv run data-product run tests/data/products_broken.csv out/broken.parquet
tests/data/products_broken.csv does not meet the contract:
- column 'name': 1 empty value, but the column is required
- column 'registered_on': 1 value is not DATE, for example '15/01/2024'
- column 'units': 1 value is not BIGINT, for example 'twenty'
```

What the pipeline guarantees:

- The header must have exactly the contract's columns, in any order.
- Every value must convert to its column's type. Empty values are accepted
  only in columns that allow them, and are written as nulls.
- Nothing is written unless the whole file meets the contract.
- The output is written under a temporary name and renamed at the end, so a
  failed run never leaves a half-written file or damages the previous one.

Limits you should know:

- Input must be comma-separated UTF-8 text. A byte order mark is fine. Other
  separators and encodings are rejected, not guessed.
- Types are DuckDB types, so dates must look like `2024-01-15`.
- The exit code is 0 on success, 1 when the input is rejected and 2 when the
  command itself is wrong.

## Scale

`uv run poe bench` measures the sample pipeline at a base size and at ten
times that size, and rewrites [`docs/benchmarks.md`](docs/benchmarks.md) with
the time and the peak memory of each one.

```console
uv run poe bench
```

The base size is 100,000 synthetic rows. To use another one:

```console
uv run poe bench --rows 500000
```

Each size runs in a new Python process, so the memory of one run cannot hide
inside another. The report also says on which machine it was measured and
what the numbers do not tell you.

## Checks

`uv run poe check` runs these steps in order and stops at the first failure:

| Step | Command | What it does |
| --- | --- | --- |
| Format | `uv run poe format-check` | Fails if a file is not in the standard format |
| Lint | `uv run poe lint` | Looks for likely mistakes with ruff |
| Types | `uv run poe types` | Checks the type annotations with mypy in strict mode |
| Tests | `uv run poe test` | Runs the tests and fails if branch coverage is under 90% |

`uv run poe format` rewrites the code in the standard format.

CI runs the same command on every pull request, on Ubuntu and Windows, with
Python 3.12, 3.13 and 3.14.

## Layout

| Path | What it holds |
| --- | --- |
| `src/data_product/cli.py` | The command line. |
| `src/data_product/contract.py` | The data contract and the checks behind it. |
| `src/data_product/pipeline.py` | The sample pipeline and its contract. |
| `tests/` | One test per behavior. `tests/data/` has a good and a broken sample file. |
| `scripts/benchmark.py` | Measures time and peak memory at two sizes. |
| `docs/benchmarks.md` | The last measurement, written by the script. |
| `pyproject.toml` | Project metadata, dependencies, tool settings and tasks. |
| `uv.lock` | Pinned versions of every dependency. |
| `.github/workflows/ci.yml` | The CI workflow. |
| `.github/dependabot.yml` | Weekly dependency updates. |

## License

[MIT](LICENSE)
