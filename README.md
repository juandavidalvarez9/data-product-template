# data-product-template

Starting point for small, tested data products: one Python package, one
command line, and a test suite that runs with a single command.

> **Status:** early. The template is being built in small pull requests.
> Today it has the package skeleton and its tests. Linting, type checks, CI,
> a sample pipeline and scale measurements arrive in the next ones.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.12 or newer (uv installs it for you if it is missing)

## Quick start

```console
uv sync
uv run pytest
uv run data-product --version
```

`uv sync` creates the virtual environment and installs the exact dependency
versions pinned in `uv.lock`.

## Layout

| Path | What it holds |
| --- | --- |
| `src/data_product/` | The package. `cli.py` is the command-line entry point. |
| `tests/` | One test per behavior. |
| `pyproject.toml` | Project metadata, dependencies and tool settings. |
| `uv.lock` | Pinned versions of every dependency. |

## License

[MIT](LICENSE)
