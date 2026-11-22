"""Starting a product from the template.

The main test does what a person would do: copy the template, run the init
script, install the dependencies and run every check in the renamed copy.
"""

import importlib.util
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

from .conftest import ROOT, copy_project, run_uv

SCRIPT = ROOT / "scripts" / "init_project.py"
TEMPLATE_NAMES = ("data_product", "data-product")


def load_script() -> ModuleType:
    """Import scripts/init_project.py, which is not part of the package."""
    spec = importlib.util.spec_from_file_location("init_project_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def template(tmp_path: Path) -> Path:
    return copy_project(tmp_path / "copy")


@pytest.fixture(scope="module")
def product(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the template, renamed once and shared by the read-only tests."""
    # The names of the first real product: longer than the template's, so
    # they also prove that the renamed code is put back in the standard format.
    root = copy_project(tmp_path_factory.mktemp("product") / "catalog")
    load_script().init_project(
        root,
        package="colombia_medicines_catalog",
        dist_name="colombia-medicines-catalog",
        command="colmed",
    )
    return root


def test_renamed_copy_passes_its_own_tests(product: Path) -> None:
    sync = run_uv(product, "sync", "--locked")
    assert sync.returncode == 0, sync.stderr

    check = run_uv(product, "run", "poe", "check")
    assert check.returncode == 0, check.stdout + check.stderr

    version = run_uv(product, "run", "colmed", "--version")
    assert version.stdout.strip() == "colmed 0.1.0"


def test_no_template_name_is_left(product: Path) -> None:
    leftovers = [
        name
        for name, content in snapshot(product).items()
        if ".venv" not in Path(name).parts
        and any(old.encode() in content for old in TEMPLATE_NAMES)
    ]

    assert leftovers == []
    assert not (product / "src" / "data_product").exists()


def test_names_go_to_the_right_places(product: Path) -> None:
    pyproject = tomllib.loads((product / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (product / "README.md").read_text(encoding="utf-8")

    package = "colombia_medicines_catalog"
    assert pyproject["project"]["name"] == "colombia-medicines-catalog"
    assert pyproject["project"]["scripts"] == {"colmed": f"{package}.cli:main"}
    assert pyproject["tool"]["coverage"]["run"]["source_pkgs"] == [package]
    assert (product / "src" / package / "cli.py").is_file()
    assert readme.startswith("# colombia-medicines-catalog\n")
    assert "uv run colmed run" in readme


def test_template_only_files_are_removed(product: Path) -> None:
    assert not (product / "scripts" / "init_project.py").exists()
    assert not (product / "scripts" / "product_readme.md").exists()
    assert not (product / "tests" / "test_init_project.py").exists()
    assert (product / "scripts" / "benchmark.py").is_file()


def test_product_readme_has_required_sections(product: Path) -> None:
    readme = (product / "README.md").read_text(encoding="utf-8")
    required = ["Problem", "Data", "Quick start", "Example", "Limits"]

    headings = re.findall(r"^## (.+)$", readme, flags=re.MULTILINE)

    assert [heading for heading in headings if heading in required] == required
    assert "Start a new product" not in headings


def test_product_starts_with_a_fresh_changelog(product: Path) -> None:
    changelog = (product / "CHANGELOG.md").read_text(encoding="utf-8")

    assert changelog.startswith("# Changelog\n")
    assert "## [Unreleased]" in changelog
    assert "- Project started from the data product template." in changelog
    assert "benchmark" not in changelog.lower()


def test_missing_product_readme_is_reported(template: Path) -> None:
    script = load_script()
    (template / "scripts" / "product_readme.md").unlink()
    before = snapshot(template)

    with pytest.raises(script.InitError, match=r"product_readme\.md is missing"):
        script.init_project(template, package="river_levels", dist_name="river-levels")

    assert snapshot(template) == before


def test_command_defaults_to_the_distribution_name(template: Path) -> None:
    load_script().init_project(
        template, package="river_levels", dist_name="river-levels"
    )

    pyproject = tomllib.loads((template / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["scripts"] == {"river-levels": "river_levels.cli:main"}


def test_new_name_may_contain_the_template_name(template: Path) -> None:
    load_script().init_project(
        template, package="data_product_next", dist_name="data-product-next"
    )

    pyproject = tomllib.loads((template / "pyproject.toml").read_text(encoding="utf-8"))
    init_file = template / "src" / "data_product_next" / "__init__.py"
    assert pyproject["project"]["name"] == "data-product-next"
    assert pyproject["project"]["scripts"] == {
        "data-product-next": "data_product_next.cli:main"
    }
    assert 'version("data-product-next")' in init_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("package", "dist_name", "command", "reason"),
    [
        ("river_levels", "River_Levels", None, "'River_Levels' is not a valid name"),
        ("river_levels", "1river", None, "'1river' is not a valid name"),
        ("river_levels", "river-levels", "river levels", "'river levels' is not a"),
        ("river-levels", "river-levels", None, "'river-levels' is not a valid Python"),
        ("class", "river-levels", None, "'class' is a Python keyword"),
        ("json", "river-levels", None, "'json' is a module of the standard library"),
        ("data_product", "river-levels", None, "is the template's own name"),
        ("river_levels", "data-product", None, "is the template's own name"),
    ],
    ids=[
        "uppercase distribution",
        "distribution starts with a digit",
        "command with a space",
        "package with a hyphen",
        "package is a keyword",
        "package shadows the standard library",
        "package is the template's",
        "distribution is the template's",
    ],
)
def test_invalid_name_is_rejected(
    template: Path, package: str, dist_name: str, command: str | None, reason: str
) -> None:
    script = load_script()
    before = snapshot(template)

    with pytest.raises(script.InitError, match=reason):
        script.init_project(
            template, package=package, dist_name=dist_name, command=command
        )

    assert snapshot(template) == before


def test_second_run_refuses(template: Path) -> None:
    script = load_script()
    script.init_project(template, package="river_levels", dist_name="river-levels")
    after_first_run = snapshot(template)

    with pytest.raises(script.InitError, match="already been initialized"):
        script.init_project(template, package="lake_levels", dist_name="lake-levels")

    assert snapshot(template) == after_first_run


def test_existing_package_folder_is_not_overwritten(template: Path) -> None:
    script = load_script()
    (template / "src" / "river_levels").mkdir()
    before = snapshot(template)

    with pytest.raises(script.InitError, match="already exists"):
        script.init_project(template, package="river_levels", dist_name="river-levels")

    assert snapshot(template) == before


def test_command_line_renames_and_says_what_to_do_next(template: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(template / "scripts" / "init_project.py"),
            "river-levels",
            "--command",
            "rivers",
        ],
        cwd=template,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "uv sync" in result.stdout
    assert (template / "src" / "river_levels" / "cli.py").is_file()
    assert not (template / "scripts" / "init_project.py").exists()


def test_command_line_reports_a_bad_name_and_exits_1(template: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(template / "scripts" / "init_project.py"), "Bad_Name"],
        cwd=template,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "'Bad_Name' is not a valid name" in result.stderr
    assert (template / "src" / "data_product").is_dir()
