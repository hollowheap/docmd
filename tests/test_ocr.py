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


def test_offline_layout_engine() -> None:
    docmd = load_docmd()

    engine = docmd.load_layout_engine()

    assert engine is not None


def test_order_lines_by_layout() -> None:
    docmd = load_docmd()

    blocks = [
        {"bbox": (50.0, 10.0, 550.0, 40.0), "class": "header", "score": 0.9},
        {"bbox": (50.0, 60.0, 250.0, 300.0), "class": "text", "score": 0.9},
        {"bbox": (300.0, 60.0, 500.0, 300.0), "class": "text", "score": 0.9},
        {"bbox": (50.0, 320.0, 550.0, 350.0), "class": "footer", "score": 0.9},
    ]

    lines = [
        {"bbox": (50.0, 15.0, 300.0, 35.0), "text": "Top Header"},
        {"bbox": (50.0, 70.0, 200.0, 90.0), "text": "Col 1 Line 1"},
        {"bbox": (300.0, 70.0, 450.0, 90.0), "text": "Col 2 Line 1"},
        {"bbox": (50.0, 100.0, 200.0, 120.0), "text": "Col 1 Line 2"},
        {"bbox": (300.0, 100.0, 450.0, 120.0), "text": "Col 2 Line 2"},
        {"bbox": (50.0, 325.0, 300.0, 345.0), "text": "Bottom Footer"},
    ]

    ordered = docmd.order_lines_by_layout(
        lines,
        page_width=600.0,
        page_height=400.0,
        layout_blocks=blocks,
    )

    texts = [line["text"] for line in ordered]
    assert texts == [
        "Top Header",
        "Col 1 Line 1",
        "Col 1 Line 2",
        "Col 2 Line 1",
        "Col 2 Line 2",
        "Bottom Footer",
    ]
