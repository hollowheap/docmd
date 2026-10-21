from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docmd"


def load_docmd() -> ModuleType:
    loader = SourceFileLoader("docmd_cli", str(SCRIPT))
    spec = spec_from_file_location("docmd_cli", SCRIPT, loader=loader)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_engine() -> None:
    docmd = load_docmd()

    engine = docmd.load_ocr_engine()

    assert engine is not None
