from __future__ import annotations

import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pymupdf

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docmd"


def run_docmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def load_docmd() -> ModuleType:
    loader = SourceFileLoader("docmd_cli", str(SCRIPT))
    spec = spec_from_file_location("docmd_cli", SCRIPT, loader=loader)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_span_extraction(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Report Title", fontsize=24)
    page.insert_text((72, 120), "Body text", fontsize=11)
    source = tmp_path / "sample.pdf"
    document.save(source)
    document.close()

    docmd = load_docmd()
    spans = docmd.extract_pdf_spans(source)

    assert any(span["text"] == "Report Title" and span["size"] > 20 for span in spans)
    assert all(span["bbox"] for span in spans)

    result = run_docmd(str(source), "--stdout")
    assert result.returncode == 0, result.stderr
    assert "Report Title" in result.stdout
    assert "Body text" in result.stdout


def test_heading_inference(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Document Title", fontsize=24)
    page.insert_text((72, 120), "Section", fontsize=18)
    page.insert_text((72, 160), "Subsection", fontsize=14)
    page.insert_text((72, 200), "Body text with enough characters to avoid OCR fallback.", fontsize=10)
    source = tmp_path / "headings.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "# Document Title" in result.stdout
    assert "## Section" in result.stdout
    assert "### Subsection" in result.stdout
    assert "Body text" in result.stdout
    assert "# Body text" not in result.stdout


def test_column_order(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    for x, y, text in (
        (72, 120, "Left one"),
        (320, 120, "Right one"),
        (72, 160, "Left two"),
        (320, 160, "Right two"),
    ):
        page.insert_text((x, y), text, fontsize=11)
    source = tmp_path / "columns.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert (
        result.stdout.index("Left one")
        < result.stdout.index("Left two")
        < result.stdout.index("Right one")
        < result.stdout.index("Right two")
    )


def test_header_footer_suppression(tmp_path: Path) -> None:
    document = pymupdf.open()
    for page_number in (1, 2):
        page = document.new_page()
        page.insert_text((72, 30), "Running Header", fontsize=9)
        page.insert_text((72, 120), f"Body page {page_number}", fontsize=11)
        page.insert_text((300, 810), f"Page {page_number}", fontsize=9)
    source = tmp_path / "margins.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "Running Header" not in result.stdout
    assert "Page 1" not in result.stdout
    assert "Page 2" not in result.stdout
    assert "Body page 1" in result.stdout
    assert "Body page 2" in result.stdout
    assert "# Body page 1" not in result.stdout


def test_page_order(tmp_path: Path) -> None:
    document = pymupdf.open()
    for page_index in range(3):
        page = document.new_page()
        page.insert_text((72, 72), f"Page {page_index} first line", fontsize=11)
        page.insert_text((72, 120), f"Page {page_index} second line", fontsize=11)
    source = tmp_path / "pages.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout", "--no-ocr")

    assert result.returncode == 0, result.stderr
    positions = [
        result.stdout.index(f"Page {page_index} {line}")
        for page_index in range(3)
        for line in ("first line", "second line")
    ]
    assert positions == sorted(positions)
