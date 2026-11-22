# 1. Tools every product starts with

- **Date:** 2026-11-22
- **Status:** accepted

## Context

This template is the starting point for a series of data products built
over several years. Each product must run with one command, check itself on
every change, work on Windows as well as Linux, and publish how it scales.
Choosing the tools again for each product would waste time and make the
products harder to compare.

## Decision

| Topic | Chosen | Not chosen | Why |
| --- | --- | --- | --- |
| Template form | A GitHub template repository that runs as it is, plus a script that renames it | Copier or Cookiecutter | With template markers in every file, the template itself cannot run or be tested. Their advantage, pushing later changes into existing products, only pays off once there are several products. |
| Python | 3.12 or newer; CI on 3.12, 3.13 and 3.14 | Claiming versions that are not tested | Only tested versions are promised. |
| Environment | uv with `uv.lock` committed | pip with requirements files, Poetry | One command rebuilds the exact environment. |
| Format and lint | ruff | flake8, black and isort | One tool instead of three. |
| Types | mypy in strict mode, run by CI on Linux and Windows | No type checks | Type errors are caught before the tests run, including code that only runs on one system. |
| Tests | pytest, with a 90% branch-coverage floor | No floor | Without a floor, coverage drops and nobody notices. |
| Tasks | Defined once in `pyproject.toml` with poethepoet; the same commands run locally and in CI | Makefile | `make` is not installed on Windows. |
| Data engine | DuckDB, with Parquet output | pandas | It checks data with SQL and writes a columnar format without loading everything into memory. |
| CI | GitHub Actions on Ubuntu and Windows, actions pinned to a full commit, Dependabot weekly | Ubuntu only | "Runs by following the README" includes Windows. |
| Container | Not yet | A Dockerfile nobody has tested | It arrives with the first product that runs as a service, built and tested in CI. |

## Consequences

- Every product starts with the same checks, so `uv run poe check` means the
  same thing everywhere.
- Improvements to the template do not reach existing products on their own.
  They are copied by hand until that becomes too costly; then Copier is
  considered again.
- Windows problems surface in CI, not on the machine of the first person who
  tries.
