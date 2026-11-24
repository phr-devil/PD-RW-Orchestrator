"""Locate non-sensitive built-in resources in an editable checkout or a Wheel.

The source checkout is authoritative for editable installs; its missing or
altered assets must fail validation, not silently fall back to bundled copies.
"""
from pathlib import Path


def data_root() -> Path:
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "pyproject.toml").is_file() and (
        source_root / "src" / "pdrw_orchestrator" / "assets.py"
    ).is_file():
        return source_root
    bundled = Path(__file__).resolve().parent / "bundled"
    if not bundled.is_dir():
        raise ValueError("ORCHESTRATOR_BUNDLED_ASSETS_UNAVAILABLE")
    return bundled
