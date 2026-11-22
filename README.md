# data-product-template

[![CI](https://github.com/juandavidalvarez9/data-product-template/actions/workflows/ci.yml/badge.svg)](https://github.com/juandavidalvarez9/data-product-template/actions/workflows/ci.yml)

Starting point for small, tested data products: one Python package, one
command line, and one command that runs every check.

A new product starts from code that already works and already proves it:

- a sample pipeline that checks a CSV file against a **data contract** and
  writes it as Parquet;
- format, lint, strict type and test checks, with a coverage floor, run by CI
  on Ubuntu and Windows;
- a benchmark that measures time and peak memory at two sizes;
- a script that renames the template to the new product;
- a product README, a data card and decision records to fill in, with tests
  that keep the README's commands honest.

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

## Start a new product

1. Create a repository from this template, or copy its files into an empty
   one.
2. Rename everything with one command. The name is the one in
   `pyproject.toml`; the Python package gets the same name with underscores.

   ```console
   uv run python scripts/init_project.py river-levels
   ```

   To give the command-line program a shorter name:

   ```console
   uv run python scripts/init_project.py river-levels --command rivers
   ```

3. Install and check the renamed project:

   ```console
   uv sync
   uv run poe check
   ```

4. Fill in `README.md` and `docs/data-card.md` for your product.

The script checks the names before it changes anything, so a bad name leaves
every file as it was. It renames the package folder, the distribution and the
command in the code, the tests, `pyproject.toml` and `uv.lock`, and puts the
code back in the standard format.

It also replaces this README with a product README whose sections are ready to
fill in: problem, data, quick start, example, how it is tested and limits. It
starts a new, empty changelog. Then it deletes itself and the files only the
template needs.

The product README links to the CI badge of a repository with the same name as
the product, so name the GitHub repository after the product.

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

The tests also read the README. They run every command in **Quick start**
except `uv run poe check`, which is what CI runs, and every line that starts
with `$ ` in a console block, and compare the output with the README. They
also check that relative links point to files that exist, and that the data
card lists the same fields as the data contract.

## Documentation

| File | What it holds |
| --- | --- |
| [`docs/data-card.md`](docs/data-card.md) | Where the data comes from, its license, its fields and its known problems. |
| [`docs/decisions/`](docs/decisions/) | Why the tools and the data checks are the way they are. |
| [`docs/benchmarks.md`](docs/benchmarks.md) | The last scale measurement. |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed in each version. |

## Layout

| Path | What it holds |
| --- | --- |
| `src/data_product/cli.py` | The command line. |
| `src/data_product/contract.py` | The data contract and the checks behind it. |
| `src/data_product/pipeline.py` | The sample pipeline and its contract. |
| `tests/` | One test per behavior. `tests/data/` has a good and a broken sample file. |
| `scripts/benchmark.py` | Measures time and peak memory at two sizes. |
| `scripts/init_project.py` | Renames the template to start a new product. |
| `scripts/product_readme.md` | The README a new product starts with. |
| `docs/` | Data card, decision records and the last scale measurement. |
| `pyproject.toml` | Project metadata, dependencies, tool settings and tasks. |
| `uv.lock` | Pinned versions of every dependency. |
| `.github/workflows/ci.yml` | The CI workflow. |
| `.github/dependabot.yml` | Weekly dependency updates. |

## Limits

- It is a Python template. Products in other languages need their own.
- The sample pipeline reads comma-separated UTF-8 files only.
- Windows is tested by CI only; macOS is not tested.
- There is no container yet. It arrives with the first product that runs as a
  service.
- Improvements to the template do not reach products that were already
  created from it. They are copied by hand.

## License

[MIT](LICENSE)
