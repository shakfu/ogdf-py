"""Tests for scripts/release_notes.py, which builds the GitHub release body in CI."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release_notes.py"
_spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
assert _spec is not None and _spec.loader is not None
release_notes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_notes)

CHANGELOG = """\
# Changelog

## [Unreleased]

### Added

- Pending thing.

## [1.10.0]

### Fixed

- Ten.

## [1.1.0]

### Fixed

- One.

## [1.0.0]

## [0.9.0]

- Nine.
"""


@pytest.fixture
def changelog(tmp_path: Path) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG)
    return path


def run(changelog: Path, version: str, *extra: str) -> tuple[int, Path]:
    out = changelog.parent / "notes.md"
    code = release_notes.main(
        [version, "--changelog", str(changelog), "-o", str(out), *extra]
    )
    return code, out


def test_extracts_only_the_named_section(changelog: Path) -> None:
    code, out = run(changelog, "1.1.0")
    assert code == 0
    assert (
        out.read_text() == "## Changes since the last Release\n\n### Fixed\n\n- One.\n"
    )


def test_version_dots_match_literally(changelog: Path) -> None:
    # A regex match of "1.1.0" could also hit "1.10.0"; the heading must match exactly.
    _, out = run(changelog, "1.10.0")
    assert "- Ten." in out.read_text()
    assert "- One." not in out.read_text()


def test_last_section_runs_to_end_of_file(changelog: Path) -> None:
    _, out = run(changelog, "0.9.0")
    assert out.read_text().endswith("\n\n- Nine.\n")


def test_custom_header(changelog: Path) -> None:
    _, out = run(changelog, "1.1.0", "--header", "What's new")
    assert out.read_text().startswith("## What's new\n\n")


@pytest.mark.parametrize("version", ["2.0.0", "1.0.0"], ids=["missing", "empty"])
def test_falls_back_to_unreleased(changelog: Path, version: str) -> None:
    code, out = run(changelog, version)
    assert code == 0
    assert "- Pending thing." in out.read_text()


def test_no_section_exits_2_without_writing(tmp_path: Path) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_text("# Changelog\n\n## [1.0.0]\n\n- One.\n")
    code, out = run(path, "2.0.0")
    assert code == 2
    assert not out.exists()
