"""Measure how the sample pipeline scales and write the result as Markdown.

Run it with `uv run poe bench`. It builds synthetic input at three sizes (one
row, the base size and the base size times a factor), runs the pipeline on
each one and writes the time and the peak memory to `docs/benchmarks.md`.

Each size runs in a new Python process. The operating system keeps one peak
memory figure per process and never lowers it, so runs that share a process
would hide each other's memory use.
"""

import argparse
import datetime
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb

from data_product.contract import quote_text
from data_product.pipeline import EXAMPLE_CONTRACT, run

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "benchmarks.md"
MEGABYTE = 1024 * 1024


@dataclass(frozen=True)
class Measurement:
    """One pipeline run at one input size."""

    scale: str
    rows: int
    input_bytes: int
    seconds: float
    peak_bytes: int


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.measure is not None:
        print(json.dumps(measure(args.measure, args.repeats)))
        return 0

    sizes = [
        ("baseline", 1),
        ("1x", args.rows),
        (f"{args.factor}x", args.rows * args.factor),
    ]
    with tempfile.TemporaryDirectory() as work:
        measurements = [
            measure_in_new_process(scale, rows, Path(work), args.repeats)
            for scale, rows in sizes
        ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_report(measurements, args.factor, args.repeats), encoding="utf-8"
    )
    print(f"Wrote {args.output}")
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--rows",
        type=at_least(1),
        default=100_000,
        help="rows in the 1x input (default: 100000)",
    )
    parser.add_argument(
        "--factor",
        type=at_least(2),
        default=10,
        help="how many times bigger the second input is (default: 10)",
    )
    parser.add_argument(
        "--repeats",
        type=at_least(1),
        default=3,
        help="runs per size; the report shows the median time (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown file to write (default: docs/benchmarks.md)",
    )
    # Used by the script itself to measure one input in a new process.
    parser.add_argument("--measure", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def at_least(minimum: int) -> Callable[[str], int]:
    """Return an argparse type that accepts whole numbers from `minimum` up."""

    def whole_number(text: str) -> int:
        value = int(text)
        if value < minimum:
            raise argparse.ArgumentTypeError(f"must be {minimum} or more")
        return value

    return whole_number


def write_synthetic_csv(path: Path, rows: int) -> None:
    """Write `rows` rows that meet the sample contract, with some empty values."""
    with duckdb.connect() as connection:
        connection.execute(
            f"""
            COPY (
                SELECT
                    i + 1 AS product_id,
                    'Artículo ' || (i + 1) AS name,
                    CASE WHEN i % 10 = 0 THEN NULL
                         ELSE DATE '2020-01-01' + CAST(i % 1500 AS INTEGER)
                    END AS registered_on,
                    CASE WHEN i % 7 = 0 THEN NULL ELSE i % 500 END AS units
                FROM range({rows}) AS numbers(i)
            ) TO {quote_text(str(path))} (FORMAT csv, HEADER true)
            """
        )


def measure_in_new_process(
    scale: str, rows: int, work: Path, repeats: int
) -> Measurement:
    source = work / f"{scale}.csv"
    write_synthetic_csv(source, rows)
    child = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--measure",
            str(source),
            "--repeats",
            str(repeats),
        ],
        stdout=subprocess.PIPE,  # the child's errors go straight to the terminal
        text=True,
        check=True,
    )
    result = json.loads(child.stdout)
    return Measurement(
        scale=scale,
        rows=result["rows"],
        input_bytes=source.stat().st_size,
        seconds=statistics.median(result["seconds"]),
        peak_bytes=result["peak_bytes"],
    )


def measure(source: Path, repeats: int) -> dict[str, object]:
    """Run the pipeline on `source` and return its times and peak memory."""
    seconds = []
    rows = 0
    with tempfile.TemporaryDirectory() as out:
        for _ in range(repeats):
            started = time.perf_counter()
            report = run(source, Path(out) / "output.parquet", EXAMPLE_CONTRACT)
            seconds.append(time.perf_counter() - started)
            rows = report.rows_out
    return {"rows": rows, "seconds": seconds, "peak_bytes": peak_memory_bytes()}


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _MemoryCounters(ctypes.Structure):
        """PROCESS_MEMORY_COUNTERS, as the Windows API defines it."""

        _fields_ = (
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        )

    def peak_memory_bytes() -> int:
        """Return the most memory this process has held, as Windows reports it."""
        counters = _MemoryCounters()
        counters.cb = ctypes.sizeof(_MemoryCounters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_MemoryCounters),
            wintypes.DWORD,
        )
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize)

else:
    import resource

    def peak_memory_bytes() -> int:
        """Return the most memory this process has held, as the system reports it."""
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports kilobytes; macOS reports bytes.
        return peak if sys.platform == "darwin" else peak * 1024


def render_report(
    measurements: Sequence[Measurement], factor: int, repeats: int
) -> str:
    baseline, small, large = measurements
    time_ratio = large.seconds / small.seconds
    memory_ratio = large.peak_bytes / small.peak_bytes
    rows = "\n".join(
        f"| {m.scale} | {m.rows:,} | {file_size(m.input_bytes)} | {m.seconds:.2f} s "
        f"| {rows_per_second(m)} | {megabytes(m.peak_bytes)} |"
        for m in measurements
    )
    return f"""\
# Scale measurements

This file is written by `uv run poe bench`. Do not edit it by hand.

| Scale | Rows | Input size | Time | Rows per second | Peak memory |
| --- | --- | --- | --- | --- | --- |
{rows}

{factor} times the rows took {time_ratio:.1f} times the time and
{memory_ratio:.1f} times the peak memory. One row already needs
{megabytes(baseline.peak_bytes)}: that is the fixed cost of Python and DuckDB.

## How it was measured

- Date: {datetime.date.today().isoformat()}
- Machine: {platform.system()} {platform.release()}, {platform.machine()}, \
{os.cpu_count()} CPU cores
- Software: Python {platform.python_version()}, DuckDB {duckdb.__version__}
- The time covers the whole pipeline: checking the input against the contract
  and writing the Parquet file. Creating the input is not counted.
- Time is the median of {repeats} {"run" if repeats == 1 else "runs"} per size.
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
"""


def rows_per_second(measurement: Measurement) -> str:
    # One row measures the fixed start-up cost, not a rate.
    if measurement.rows == 1:
        return "-"
    return f"{measurement.rows / measurement.seconds:,.0f}"


def file_size(size: int) -> str:
    return megabytes(size) if size >= MEGABYTE else f"{size / 1024:.1f} KB"


def megabytes(size: int) -> str:
    return f"{size / MEGABYTE:.1f} MB"


if __name__ == "__main__":
    raise SystemExit(main())
