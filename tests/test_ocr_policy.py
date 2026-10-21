from __future__ import annotations

import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pymupdf

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docmd"


def run_docmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def make_scanned_pdf(tmp_path: Path) -> Path:
    source = pymupdf.open()
    page = source.new_page()
    page.insert_text((72, 100), "SCANNED HEADING", fontsize=28)
    page.insert_text((72, 160), "Scanned body text", fontsize=14)
    pixmap = page.get_pixmap(dpi=200)
    image = pixmap.tobytes("png")
    source.close()

    scanned = pymupdf.open()
    page = scanned.new_page(
        width=pixmap.width * 72 / 200,
        height=pixmap.height * 72 / 200,
    )
    page.insert_image(page.rect, stream=image)
    path = tmp_path / "scanned.pdf"
    scanned.save(path)
    scanned.close()
    return path


def test_page_fallback(tmp_path: Path) -> None:
    source = make_scanned_pdf(tmp_path)

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "SCANNED HEADING" in result.stdout
    assert "Scanned body text" in result.stdout
    assert "# SCANNED HEADING" in result.stdout

    no_ocr = run_docmd(str(source), "--stdout", "--no-ocr")
    assert no_ocr.returncode == 0, no_ocr.stderr
    assert "SCANNED HEADING" not in no_ocr.stdout
    assert "> *[Image Text]*" not in no_ocr.stdout


def test_image_caption(tmp_path: Path) -> None:
    label = pymupdf.open()
    page = label.new_page()
    page.insert_text((72, 100), "DIAGRAM LABEL", fontsize=28)
    pixmap = page.get_pixmap(dpi=200)
    image = pixmap.tobytes("png")
    label.close()

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "This page contains enough digital text to avoid the OCR fallback policy.",
        fontsize=11,
    )
    page.insert_image(pymupdf.Rect(72, 120, 400, 260), stream=image)
    source = tmp_path / "image.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "![](data:image/png;base64," in result.stdout
    assert "> *[Image Text]*: DIAGRAM LABEL" in result.stdout
    assert result.stdout.index("![](data:image/png;base64,") < result.stdout.index(
        "> *[Image Text]*:"
    )


def test_overlay_reconciliation(tmp_path: Path) -> None:
    label = pymupdf.open()
    page = label.new_page()
    page.insert_text((72, 100), "DIAGRAM LABEL", fontsize=28)
    pixmap = page.get_pixmap(dpi=200)
    image = pixmap.tobytes("png")
    label.close()

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "This page has enough searchable digital text to avoid page OCR fallback.",
        fontsize=11,
    )
    page.insert_image(pymupdf.Rect(72, 120, 400, 260), stream=image)
    page.insert_text((80, 180), "DIAGRAM LABEL", fontsize=28, render_mode=3)
    source = tmp_path / "overlay.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("DIAGRAM LABEL") == 1
    assert "> *[Image Text]*:" not in result.stdout
    assert "![](data:image/png;base64," in result.stdout


def load_docmd():
    loader = SourceFileLoader("docmd_cli", str(SCRIPT))
    spec = spec_from_file_location("docmd_cli", SCRIPT, loader=loader)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeEngine:
    def __init__(self, items: list[tuple[list[list[int]], str, float]]) -> None:
        self.items = items

    def __call__(self, data: bytes):
        return (self.items, None)


class FakePixmap:
    width = 100
    height = 50

    def tobytes(self, output: str) -> bytes:
        return b"png"


class FakePage:
    number = 3

    def __init__(self) -> None:
        self.rect = SimpleNamespace(width=72.0, height=36.0)

    def get_pixmap(self, dpi: int = 200) -> FakePixmap:
        return FakePixmap()


def test_score_filter() -> None:
    docmd = load_docmd()
    engine = FakeEngine(
        [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "KEEP", 0.9),
            ([[0, 20], [10, 20], [10, 30], [0, 30]], "LOW", 0.2),
            ([[0, 40], [10, 40], [10, 50], [0, 50]], "   ", 0.99),
        ]
    )

    assert docmd.ocr_image_text(engine, b"image") == "KEEP"

    lines = docmd.ocr_pdf_page(FakePage(), engine)
    assert len(lines) == 1
    assert lines[0]["text"] == "KEEP"
    assert lines[0]["page"] == 3


def test_no_ocr_keeps_images(tmp_path: Path) -> None:
    label = pymupdf.open()
    page = label.new_page()
    page.insert_text((72, 100), "DIAGRAM LABEL", fontsize=28)
    pixmap = page.get_pixmap(dpi=200)
    image = pixmap.tobytes("png")
    label.close()

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "This page contains enough digital text to avoid the OCR fallback policy.",
        fontsize=11,
    )
    page.insert_image(pymupdf.Rect(72, 120, 400, 260), stream=image)
    source = tmp_path / "image.pdf"
    document.save(source)
    document.close()

    no_ocr = run_docmd(str(source), "--stdout", "--no-ocr")

    assert no_ocr.returncode == 0, no_ocr.stderr
    assert "![](data:image/png;base64," in no_ocr.stdout
    assert "> *[Image Text]*:" not in no_ocr.stdout
    assert "This page contains enough digital text" in no_ocr.stdout

    no_images = run_docmd(str(source), "--stdout", "--no-images")

    assert no_images.returncode == 0, no_images.stderr
    assert "![" not in no_images.stdout
    assert "> *[Image Text]*:" not in no_images.stdout
    assert "This page contains enough digital text" in no_images.stdout
