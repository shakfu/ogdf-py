"""Tests for the installation diagnostic report (`ogdf.about()`)."""

import subprocess
import sys

import ogdf


def test_about_reports_versions():
    info = ogdf.about()
    # The compiled-in version and the installed distribution metadata both come
    # from pyproject.toml, so a mismatch means the extension is stale.
    assert info["package_version"] == ogdf.__version__
    # OGDF's own compiled-in version, e.g. "2025.10".
    assert info["ogdf_version"]
    # The pinned tag is baked in by CMake from scripts/ogdf-tag.txt.
    assert info["ogdf_tag"] and info["ogdf_tag"] != "unknown"


def test_about_reports_platform_and_compiler():
    info = ogdf.about()
    for key in ("platform", "machine", "python_version", "compiler"):
        assert info[key], f"{key} should not be empty"
    assert info["extension_path"] is not None


def test_about_reports_capabilities():
    info = ogdf.about()
    caps = info["capabilities"]
    # Sanity floors: the curated surface is far larger than these.
    assert caps["layouts"] >= 10
    assert caps["functions"] >= 50
    assert caps["io"] >= 10
    assert caps["types"] >= 5
    names = info["capability_names"]
    assert "FMMMLayout" in names["layouts"]
    assert "dijkstra" in names["functions"]
    assert "to_svg" in names["io"]
    assert "Graph" in names["types"]
    assert set(caps) == set(names)


def test_about_text_is_printable():
    text = ogdf.about_text()
    assert "ogdf-py installation report" in text
    assert ogdf.__version__ in text


def test_python_m_ogdf_prints_report():
    out = subprocess.run(
        [sys.executable, "-m", "ogdf"], capture_output=True, text=True, check=True
    )
    assert "ogdf-py installation report" in out.stdout
