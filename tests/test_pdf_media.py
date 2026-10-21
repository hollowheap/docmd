from __future__ import annotations

import base64
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pymupdf

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docmd"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
)


def load_docmd() -> ModuleType:
    loader = SourceFileLoader("docmd_cli", str(SCRIPT))
    spec = spec_from_file_location("docmd_cli", SCRIPT, loader=loader)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePage:
    def __init__(self, xrefs: list[int], number: int) -> None:
        self._xrefs = xrefs
        self.number = number

    def get_images(self, full: bool = True) -> list[tuple[int, ...]]:
        return [(xref, 0, 0, 0, 0, 0, 0) for xref in self._xrefs]


class FakeDocument:
    def __init__(self, pages: list[FakePage]) -> None:
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)

    def close(self) -> None:
        pass

    def extract_image(self, xref: int) -> dict[str, object]:
        if xref == 4:
            raise RuntimeError("broken image")
        return {"image": PNG, "ext": "jpeg" if xref == 2 else "png"}


def test_xref_dedup(monkeypatch) -> None:
    docmd = load_docmd()
    document = FakeDocument(
        [
            FakePage([1, 1, 0, -1, 4, 2], number=0),
            FakePage([1], number=1),
        ]
    )
    monkeypatch.setattr(docmd, "open_pdf", lambda source, password=None: document)

    blocks = docmd.pdf_image_blocks(Path("fake.pdf"), use_ocr=False)

    assert len(blocks) == 3
    assert blocks[0] == (0, f"![](data:image/png;base64,{base64.b64encode(PNG).decode()})")
    assert blocks[1][0] == 0
    assert blocks[1][1].startswith("![](data:image/jpeg;base64,")
    assert blocks[2][0] == 1
    assert blocks[2][1].startswith("![](data:image/png;base64,")


def run_docmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def test_image_page_order(tmp_path: Path) -> None:
    label = pymupdf.open()
    label_page = label.new_page()
    label_page.insert_text((72, 100), "FIGURE", fontsize=24)
    image = label_page.get_pixmap(dpi=72).tobytes("png")
    label.close()

    document = pymupdf.open()
    for index in (1, 2):
        page = document.new_page()
        page.insert_text((72, 72), f"Page {index} body text", fontsize=11)
        page.insert_image(pymupdf.Rect(72, 120, 300, 300), stream=image)
    source = tmp_path / "pages.pdf"
    document.save(source)
    document.close()

    result = run_docmd(str(source), "--stdout", "--no-ocr")

    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    images = [
        match.start()
        for match in re.finditer(re.escape("![](data:image/png;base64,"), stdout)
    ]
    assert len(images) == 2
    assert stdout.index("Page 1 body text") < images[0]
    assert images[0] < stdout.index("Page 2 body text") < images[1]
