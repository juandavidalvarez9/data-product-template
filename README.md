# data-product-template

Starting point for small, tested data products: one Python package, one
command line, and one command that runs every check.

> **Status:** early. The template is being built in small pull requests.
> Today it has the package skeleton, the checks and CI. A sample pipeline
> and scale measurements arrive in the next ones.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.12 or newer (uv installs it for you if it is missing)

## Quick start

```console
uv sync
uv run poe check
uv run data-product --version
```

`uv sync` creates the virtual environment and installs the exact dependency
versions pinned in `uv.lock`.

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
| `src/data_product/` | The package. `cli.py` is the command-line entry point. |
| `tests/` | One test per behavior. |
| `pyproject.toml` | Project metadata, dependencies, tool settings and tasks. |
| `uv.lock` | Pinned versions of every dependency. |
| `.github/workflows/ci.yml` | The CI workflow. |
| `.github/dependabot.yml` | Weekly dependency updates. |

## License

[MIT](LICENSE)
