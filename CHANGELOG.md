# Changelog

All notable changes to this project are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Package skeleton with a command line that reports its version
  ([#1](https://github.com/juandavidalvarez9/data-product-template/pull/1)).
- One command for every check: format, lint, strict types and tests with a
  90% branch-coverage floor, run by CI on Ubuntu and Windows with Python 3.12,
  3.13 and 3.14, and weekly Dependabot updates
  ([#2](https://github.com/juandavidalvarez9/data-product-template/pull/2)).
- Data contract and a sample pipeline from CSV to Parquet, with
  `data-product run SOURCE DEST`
  ([#4](https://github.com/juandavidalvarez9/data-product-template/pull/4)).
- Scale benchmark at one row, a base size and ten times that size, with its
  report in `docs/benchmarks.md`
  ([#5](https://github.com/juandavidalvarez9/data-product-template/pull/5)).
- Script that renames the template to start a new product
  ([#6](https://github.com/juandavidalvarez9/data-product-template/pull/6)).
- Product README, data card, decision records and this changelog. Tests check
  that the README commands run and print what the README shows.

### Changed

- The build backend `uv_build` may now be any version below 0.14
  ([#3](https://github.com/juandavidalvarez9/data-product-template/pull/3)).
