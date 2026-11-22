"""The scale benchmark: it must run on any machine and write a complete report.

The tests check the shape of the report, never how fast the machine is.
"""

import importlib.util
import platform
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark.py"
COMMITTED_REPORT = ROOT / "docs" / "benchmarks.md"


def run_benchmark(*args: str, output: Path) -> subprocess.CompletedProcess[str]:
    """Run the script, always writing to `output`.

    Every run names its output, so a test can never overwrite the committed
    report, even when the code under test is broken.
    """
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )


def load_script() -> ModuleType:
    """Import scripts/benchmark.py, which is not part of the package."""
    spec = importlib.util.spec_from_file_location("benchmark_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_table(markdown: str) -> dict[str, dict[str, str]]:
    """Return the rows of the first Markdown table, keyed by their first cell."""
    lines = [line for line in markdown.splitlines() if line.startswith("|")]
    header, _separator, *rows = [
        [cell.strip() for cell in line.strip("|").split("|")] for line in lines
    ]
    return {row[0]: dict(zip(header, row, strict=True)) for row in rows}


@pytest.fixture(scope="module")
def output(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("benchmark") / "docs" / "benchmarks.md"
    result = run_benchmark(
        "--rows", "200", "--factor", "10", "--repeats", "1", output=path
    )
    assert result.returncode == 0, result.stderr
    return path


@pytest.fixture(scope="module")
def table(output: Path) -> dict[str, dict[str, str]]:
    return parse_table(output.read_text(encoding="utf-8"))


def test_scale_factor_multiplies_rows(table: dict[str, dict[str, str]]) -> None:
    assert table["1x"]["Rows"] == "200"
    assert table["10x"]["Rows"] == "2,000"


def test_report_has_time_and_peak_memory_for_both_scales(
    table: dict[str, dict[str, str]],
) -> None:
    for scale in ("1x", "10x"):
        seconds = float(table[scale]["Time"].removesuffix(" s"))
        megabytes = float(table[scale]["Peak memory"].removesuffix(" MB"))
        assert seconds > 0
        assert megabytes > 0


def test_report_has_a_one_row_baseline(table: dict[str, dict[str, str]]) -> None:
    assert table["baseline"]["Rows"] == "1"
    assert table["baseline"]["Rows per second"] == "-"
    assert float(table["baseline"]["Peak memory"].removesuffix(" MB")) > 0


def test_report_shows_the_rate_and_the_input_size(
    table: dict[str, dict[str, str]],
) -> None:
    assert int(table["10x"]["Rows per second"].replace(",", "")) > 0
    assert table["10x"]["Input size"].endswith(" KB")


def test_report_compares_the_two_scales(output: Path) -> None:
    text = output.read_text(encoding="utf-8")

    assert "10 times the rows took" in text


def test_report_says_how_it_was_measured(output: Path) -> None:
    text = output.read_text(encoding="utf-8")

    assert f"Python {platform.python_version()}" in text
    assert "DuckDB" in text
    assert platform.system() in text
    assert "new Python process" in text


def test_benchmark_leaves_only_the_report(output: Path) -> None:
    assert [path.name for path in output.parent.iterdir()] == ["benchmarks.md"]


@pytest.mark.parametrize(
    "arguments",
    [("--rows", "0"), ("--factor", "1"), ("--repeats", "0"), ("--rows", "many")],
    ids=["zero rows", "factor of one", "zero repeats", "rows not a number"],
)
def test_benchmark_rejects_bad_arguments(
    arguments: tuple[str, ...], tmp_path: Path
) -> None:
    report = tmp_path / "benchmarks.md"

    result = run_benchmark(*arguments, output=report)

    assert result.returncode == 2
    assert arguments[0] in result.stderr
    assert not report.exists()


def test_committed_report_compares_two_different_sizes() -> None:
    table = parse_table(COMMITTED_REPORT.read_text(encoding="utf-8"))
    scales = [scale for scale in table if scale not in ("baseline", "1x")]

    assert list(table)[:2] == ["baseline", "1x"]
    assert len(scales) == 1, f"expected one larger size, found {list(table)}"
    factor = int(scales[0].removesuffix("x"))
    rows = {scale: int(table[scale]["Rows"].replace(",", "")) for scale in table}
    assert factor >= 2
    assert rows[scales[0]] == factor * rows["1x"]


def test_time_comes_from_the_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    benchmark = load_script()
    ticks = iter([10.0, 10.5, 20.0, 22.0])
    fake_clock = SimpleNamespace(perf_counter=lambda: next(ticks))
    monkeypatch.setattr(benchmark, "time", fake_clock)
    source = tmp_path / "input.csv"
    benchmark.write_synthetic_csv(source, 5)

    result = benchmark.measure(source, repeats=2)

    assert result["seconds"] == [0.5, 2.0]
    assert result["rows"] == 5
    assert result["peak_bytes"] > 0
