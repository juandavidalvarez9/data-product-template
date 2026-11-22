# Scale measurements

This file is written by `uv run poe bench`. Do not edit it by hand.

| Scale | Rows | Input size | Time | Rows per second | Peak memory |
| --- | --- | --- | --- | --- | --- |
| baseline | 1 | 0.1 KB | 0.03 s | - | 73.2 MB |
| 1x | 100,000 | 3.4 MB | 0.12 s | 865,484 | 85.6 MB |
| 10x | 1,000,000 | 35.4 MB | 0.64 s | 1,565,023 | 212.7 MB |

10 times the rows took 5.5 times the time and
2.5 times the peak memory. One row already needs
73.2 MB: that is the fixed cost of Python and DuckDB.

## How it was measured

- Date: 2026-11-22
- Machine: Linux 6.18.44-fc-v726, x86_64, 2 CPU cores
- Software: Python 3.12.3, DuckDB 2.0.1
- The time covers the whole pipeline: checking the input against the contract
  and writing the Parquet file. Creating the input is not counted.
- Time is the median of 3 runs per size.
- Each size runs in a new Python process. Peak memory is the highest figure
  the operating system recorded for that process, with Python and DuckDB
  included.

## Limits

- The input is synthetic: four columns, short text and some empty values.
  Real data with long text or many columns will behave differently.
- These are a few runs on one machine. Expect the numbers to move between
  runs and between machines. Compare the ratios, not the exact values.
- Peak memory grows with the input. The pipeline sets no memory limit, so
  DuckDB takes more memory when more is free.
