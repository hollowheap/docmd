from __future__ import annotations

import os
import subprocess
import sys
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


def test_ort_telemetry_disabled_before_onnxruntime_import() -> None:
    env = os.environ.copy()
    env.pop("ORT_DISABLE_TELEMETRY", None)
    probe = (
        "import os, sys; "
        "from importlib.machinery import SourceFileLoader; "
        "from importlib.util import module_from_spec, spec_from_file_location; "
        f"spec = spec_from_file_location('docmd_cli', {str(SCRIPT)!r}, "
        f"loader=SourceFileLoader('docmd_cli', {str(SCRIPT)!r})); "
        "mod = module_from_spec(spec); "
        "spec.loader.exec_module(mod); "
        "assert os.environ.get('ORT_DISABLE_TELEMETRY') == '1'; "
        "assert 'onnxruntime' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    env["ORT_DISABLE_TELEMETRY"] = "0"
    preserve_probe = (
        "import os; "
        "from importlib.machinery import SourceFileLoader; "
        "from importlib.util import module_from_spec, spec_from_file_location; "
        f"spec = spec_from_file_location('docmd_cli', {str(SCRIPT)!r}, "
        f"loader=SourceFileLoader('docmd_cli', {str(SCRIPT)!r})); "
        "mod = module_from_spec(spec); "
        "spec.loader.exec_module(mod); "
        "assert os.environ.get('ORT_DISABLE_TELEMETRY') == '0'"
    )
    preserved = subprocess.run(
        [sys.executable, "-c", preserve_probe],
        env=env,
        capture_output=True,
        text=True,
    )
    assert preserved.returncode == 0, preserved.stderr
