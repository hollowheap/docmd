from __future__ import annotations

import base64
import os
import subprocess
import sys
import zipfile
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
from pathlib import Path
from types import ModuleType

import pymupdf
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docmd"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
)


def run_docmd(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=merged,
    )


def load_docmd() -> ModuleType:
    loader = SourceFileLoader("docmd_review", str(SCRIPT))
    spec = spec_from_file_location("docmd_review", SCRIPT, loader=loader)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ocr_merges_against_digital_text(tmp_path: Path, monkeypatch) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 120), "Digital One", fontsize=11)
    page.insert_text((72, 150), "Digital Two", fontsize=11)
    source = tmp_path / "merge.pdf"
    document.save(source)
    document.close()

    docmd = load_docmd()

    def fake_ocr(page, engine, digital_texts=None, max_image_pixels=None):
        return [
            {
                "text": "Digital One",
                "size": 99.0,
                "bbox": (72.0, 120.0, 200.0, 138.0),
                "page": page.number,
                "page_height": page.rect.height,
                "page_width": page.rect.width,
                "ocr": True,
            },
            {
                "text": "OCR Only",
                "size": 12.0,
                "bbox": (72.0, 200.0, 200.0, 215.0),
                "page": page.number,
                "page_height": page.rect.height,
                "page_width": page.rect.width,
                "ocr": True,
            },
        ]

    monkeypatch.setattr(docmd, "ocr_pdf_page", fake_ocr)
    lines = docmd.extract_pdf_lines(
        source, use_ocr=True, ocr_engine=object(), layout_engine=False
    )
    texts = [line["text"] for line in lines]

    assert texts.count("Digital One") == 1
    assert "OCR Only" in texts
    digital = next(line for line in lines if line["text"] == "Digital One")
    assert digital["size"] != 99.0
    assert not digital.get("ocr")


def test_ocr_page_failure_is_visible(tmp_path: Path, monkeypatch) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 120), "Tiny", fontsize=11)
    source = tmp_path / "ocr-failure.pdf"
    document.save(source)
    document.close()

    docmd = load_docmd()
    monkeypatch.setattr(docmd, "ocr_pdf_page", lambda *args, **kwargs: None)
    markdown = docmd.convert_pdf(
        source,
        include_images=False,
        use_ocr=True,
        ocr_engine=object(),
        layout_engine=False,
    )

    assert "<!-- OCR failed for page 1 -->" in markdown


def test_pdf_table_and_paragraph_recovery(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    for row, y in enumerate((120, 150, 180, 210)):
        page.insert_text((72, y), f"Item {row}", fontsize=11)
        page.insert_text((320, y), f"Value {row}", fontsize=11)
    page.insert_text((72, 300), "Paragraph one.", fontsize=11)
    page.insert_text((72, 320), "Paragraph two.", fontsize=11)
    page.insert_text((72, 440), "Separate paragraph.", fontsize=11)
    page.insert_text((72, 500), "\u2022 Bullet item", fontsize=11)
    source = tmp_path / "structure.pdf"
    document.save(source)
    document.close()

    docmd = load_docmd()
    markdown = docmd.convert_pdf(
        source, include_images=False, use_ocr=False, layout_engine=False
    )

    assert "| Item 0 | Value 0 |" in markdown
    assert "| Item 3 | Value 3 |" in markdown
    assert "Paragraph one. Paragraph two." in markdown
    assert "Paragraph one. Paragraph two. Separate paragraph." not in markdown
    assert "- Bullet item" in markdown


def test_pdf_layout_function_is_wired(tmp_path: Path, monkeypatch) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 120), "Left one", fontsize=11)
    page.insert_text((320, 120), "Right one", fontsize=11)
    page.insert_text((72, 160), "Left two", fontsize=11)
    page.insert_text((320, 160), "Right two", fontsize=11)
    page.insert_text((72, 200), "More text to avoid OCR fallback.", fontsize=11)
    source = tmp_path / "layout.pdf"
    document.save(source)
    document.close()

    docmd = load_docmd()
    blocks = [
        {"bbox": (50.0, 50.0, 250.0, 300.0), "class": "text", "score": 0.9},
        {"bbox": (300.0, 50.0, 550.0, 300.0), "class": "text", "score": 0.9},
    ]
    monkeypatch.setattr(
        docmd,
        "layout_blocks_for_page",
        lambda page, engine, max_image_pixels=None: blocks,
    )
    lines = docmd.extract_pdf_lines(
        source, use_ocr=False, layout_engine=object()
    )
    texts = [line["text"] for line in lines]

    assert texts.index("Left one") < texts.index("Left two") < texts.index(
        "Right one"
    ) < texts.index("Right two")


def test_normalize_typography_preserves_meaning(tmp_path: Path) -> None:
    docmd = load_docmd()
    source = (
        "\u201cquoted\u201d \u2013 dash\u2026 H\u2082O x\u00b2 a\u00b7b 3 \u00d7 4 \u2192 here\n"
        "`H\u2082O \u2192 x\u00b2`\n"
        "```\nH\u2082O \u2192 x\u00b2\n```\n"
        "https://example.com/a\u2192b\n"
    )

    result = docmd.normalize_typography(source)

    assert '"quoted" - dash... H\u2082O x\u00b2 a\u00b7b 3 \u00d7 4 \u2192 here' in result
    assert "`H\u2082O \u2192 x\u00b2`" in result
    assert "```\nH\u2082O \u2192 x\u00b2\n```" in result
    assert "https://example.com/a\u2192b" in result

    document = Document()
    document.add_paragraph("\u201cquoted\u201d")
    raw = tmp_path / "quotes.docx"
    document.save(raw)
    default = run_docmd(str(raw), "--stdout")
    assert default.returncode == 0, default.stderr
    assert '"quoted"' in default.stdout
    preserved = run_docmd(str(raw), "--stdout", "--no-sanitize")
    assert preserved.returncode == 0, preserved.stderr
    assert "\u201cquoted\u201d" in preserved.stdout


def test_verify_covers_quoted_single_column_reference_and_html(
    tmp_path: Path,
) -> None:
    docmd = load_docmd()

    assert docmd.verify_markdown("| A |\n| --- |\n| B |\n", tmp_path) == []
    assert docmd.verify_markdown("| A |\n| --- |\n| B | C |\n", tmp_path) == [
        docmd.TABLE_ERROR
    ]
    assert docmd.verify_markdown(
        "> | A | B |\n> | --- | --- |\n> | C |\n", tmp_path
    ) == [docmd.TABLE_ERROR]
    assert docmd.verify_markdown("[x][id]\n\n[id]: missing.png\n", tmp_path) == [
        "missing asset: missing.png"
    ]
    assert docmd.verify_markdown('<img src="missing.png">', tmp_path) == [
        "missing asset: missing.png"
    ]
    errors, counts = docmd.verify_markdown_counts(
        "| A |\n| --- |\n| B |\n", tmp_path
    )
    assert errors == []
    assert counts["tables"] == 1


def test_batch_reports_earliest_failure_in_sorted_order(tmp_path: Path) -> None:
    source = tmp_path / "input"
    source.mkdir()

    before = Document()
    before.add_paragraph("Before")
    before.save(source / "0-before.docx")

    encrypted = pymupdf.open()
    encrypted.new_page().insert_text((72, 72), "Secret")
    encrypted.save(
        source / "a-encrypted.pdf",
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="secret",
    )
    encrypted.close()

    (source / "b-corrupt.docx").write_bytes(b"not a document")
    after = Document()
    after.add_paragraph("After")
    after.save(source / "z-after.docx")

    out = tmp_path / "out"
    for _ in range(5):
        result = run_docmd(str(source), "-o", str(out), "--jobs", "2", "--no-ocr")
        assert result.returncode == 3, result.stderr
        assert (out / "0-before.md").is_file()
        assert not (out / "a-encrypted.md").exists()
        assert not (out / "b-corrupt.md").exists()
        assert not (out / "z-after.md").exists()


def test_empty_pdf_is_corrupt_and_budgets_are_enforced(tmp_path: Path) -> None:
    blank = pymupdf.open()
    blank.new_page()
    empty_source = tmp_path / "blank.pdf"
    blank.save(empty_source)
    blank.close()

    empty = run_docmd(str(empty_source), "--stdout", "--no-ocr")
    assert empty.returncode == 2
    assert "no content could be extracted" in empty.stderr

    two_pages = pymupdf.open()
    two_pages.new_page().insert_text((72, 72), "Page one with enough text to read.")
    two_pages.new_page().insert_text((72, 72), "Page two with enough text to read.")
    two_source = tmp_path / "two.pdf"
    two_pages.save(two_source)
    two_pages.close()

    pages = run_docmd(
        str(two_source),
        "--stdout",
        "--no-ocr",
        env={"DOCMD_MAX_PAGES": "1"},
    )
    assert pages.returncode == 1
    assert "page budget exceeded" in pages.stderr

    size = run_docmd(
        str(two_source),
        "--stdout",
        "--no-ocr",
        env={"DOCMD_MAX_BYTES": "1"},
    )
    assert size.returncode == 1
    assert "byte budget exceeded" in size.stderr


def test_docmd_password_environment_is_honoured(tmp_path: Path) -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Secret body")
    source = tmp_path / "secret.pdf"
    document.save(
        source,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="secret",
    )
    document.close()

    result = run_docmd(
        str(source), "--stdout", "--no-ocr", env={"DOCMD_PASSWORD": "secret"}
    )

    assert result.returncode == 0, result.stderr
    assert "Secret body" in result.stdout


def test_ocr_configuration_is_validated(tmp_path: Path) -> None:
    document = Document()
    document.add_paragraph("Body")
    source = tmp_path / "body.docx"
    document.save(source)

    device = run_docmd(str(source), "--stdout", env={"DOCMD_OCR_DEVICE": "bogus"})
    assert device.returncode == 1
    assert "DOCMD_OCR_DEVICE" in device.stderr
    assert "bogus" in device.stderr

    model = run_docmd(str(source), "--stdout", env={"DOCMD_OCR_MODEL": "bogus"})
    assert model.returncode == 1
    assert "DOCMD_OCR_MODEL" in model.stderr


def test_docx_inline_formatting_links_and_table_images(tmp_path: Path) -> None:
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("Bold").bold = True
    paragraph.add_run(" and ")
    paragraph.add_run("italic").italic = True
    paragraph.add_run(" and ")
    code = paragraph.add_run("code")
    code.font.name = "Consolas"

    linked = document.add_paragraph("See ")
    hyperlink = OxmlElement("w:hyperlink")
    relation = document.part.relate_to(
        "https://example.com", RELATIONSHIP_TYPE.HYPERLINK, is_external=True
    )
    hyperlink.set(qn("r:id"), relation)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "the site"
    run.append(text)
    hyperlink.append(run)
    linked._p.append(hyperlink)
    document.add_paragraph("Before table")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).paragraphs[0].add_run().add_picture(BytesIO(PNG))
    document.add_paragraph("After table")

    source = tmp_path / "inline.docx"
    document.save(source)
    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "**Bold**" in result.stdout
    assert "*italic*" in result.stdout
    assert "`code`" in result.stdout
    assert "[the site](https://example.com)" in result.stdout
    assert "data:image/png;base64," in result.stdout


def add_footnote(source: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}

    document_xml = files["word/document.xml"].decode("utf-8")
    note_run = (
        '<w:p><w:r><w:t>Body with a note.</w:t></w:r>'
        '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'
        '<w:footnoteReference w:id="1"/></w:r></w:p>'
    )
    document_xml = document_xml.replace("<w:sectPr", note_run + "<w:sectPr", 1)
    files["word/document.xml"] = document_xml.encode("utf-8")

    files["word/footnotes.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:footnote w:id="-1" w:type="separator"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
        '<w:footnote w:id="0" w:type="continuationSeparator"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
        '<w:footnote w:id="1"><w:p><w:r><w:t>Footnote text.</w:t></w:r></w:p></w:footnote>'
        "</w:footnotes>"
    ).encode("utf-8")

    content_types = files["[Content_Types].xml"].decode("utf-8")
    content_types = content_types.replace(
        "</Types>",
        '<Override PartName="/word/footnotes.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
        "</Types>",
        1,
    )
    files["[Content_Types].xml"] = content_types.encode("utf-8")

    relationships = files["word/_rels/document.xml.rels"].decode("utf-8")
    relationships = relationships.replace(
        "</Relationships>",
        '<Relationship Id="rIdFootnotes" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" '
        'Target="footnotes.xml"/></Relationships>',
        1,
    )
    files["word/_rels/document.xml.rels"] = relationships.encode("utf-8")

    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def test_docx_footnotes_are_emitted(tmp_path: Path) -> None:
    document = Document()
    document.add_paragraph("Before note.")
    source = tmp_path / "notes.docx"
    document.save(source)
    add_footnote(source)

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "Body with a note.[^1]" in result.stdout
    assert "[^1]: Footnote text." in result.stdout


def test_pptx_visual_order_chart_and_multiline_notes(tmp_path: Path) -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    right = slide.shapes.add_textbox(Inches(5), Inches(1), Inches(2), Inches(1))
    right.text = "Right box"
    left = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(2), Inches(1))
    left.text = "Left box"
    chart_data = CategoryChartData()
    chart_data.categories = ["A", "B"]
    chart_data.add_series("Score", (10, 20))
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(1),
        Inches(3),
        Inches(4),
        Inches(2),
        chart_data,
    ).chart
    chart.has_title = False
    slide.notes_slide.notes_text_frame.text = "First note\nSecond note"
    source = tmp_path / "deck.pptx"
    presentation.save(source)

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert result.stdout.index("Left box") < result.stdout.index("Right box")
    assert "| Category | Score |" in result.stdout
    assert "| A | 10 |" in result.stdout
    assert "> Second note" in result.stdout


def test_reconversion_removes_stale_generated_assets(tmp_path: Path) -> None:
    docmd = load_docmd()
    output = tmp_path / "report.md"
    assets = tmp_path / "report.assets"
    assets.mkdir()
    (assets / "keep.txt").write_text("keep", encoding="utf-8")
    first = (
        f"![a](data:image/png;base64,{base64.b64encode(PNG).decode()})\n"
        f"![b](data:image/png;base64,{base64.b64encode(PNG).decode()})\n"
    )
    docmd.write_markdown(first, output)
    assert (assets / "image-002.png").is_file()

    second = f"![a](data:image/png;base64,{base64.b64encode(PNG).decode()})\n"
    docmd.write_markdown(second, output)

    assert sorted(path.name for path in assets.iterdir()) == [
        "image-001.png",
        "keep.txt",
    ]
