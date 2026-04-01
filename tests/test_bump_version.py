from pathlib import Path
from types import ModuleType

from scripts import bump_version as bv


def test_parse_and_format_pre():
    parts = bv.parse_version("1.2.3rc4")
    assert bv.format_version(*parts) == "1.2.3rc4"


def test_bump_minor_and_finalize():
    assert bv.bump_version("1.2.3", "minor", None, False) == "1.3.0"
    assert bv.bump_version("1.2.3rc1", "patch", None, True) == "1.2.3"


def test_update_pyproject_version(tmp_path, monkeypatch):
    py = tmp_path / "pyproject.toml"
    py.write_text('[project]\nname = "pkg"\nversion = "0.1.0"\n', encoding="utf-8")
    monkeypatch.setattr(bv, "PYPROJECT", py, raising=False)
    bv.update_pyproject_version("0.2.0")
    assert 'version = "0.2.0"' in py.read_text(encoding="utf-8")


def test_update_nix_version(tmp_path, monkeypatch):
    nix = tmp_path / "drawiterm.nix"
    nix.write_text('  version = "0.1.0";\n', encoding="utf-8")
    monkeypatch.setattr(bv, "NIX_FILE", nix, raising=False)
    bv.update_nix_version("0.2.0")
    assert 'version = "0.2.0";' in nix.read_text(encoding="utf-8")
