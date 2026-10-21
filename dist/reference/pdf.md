# PDF Reference

`docmd` converts PDFs into GitHub Flavored Markdown using font size, bounding
boxes, and optional offline OCR.

## Supported elements

- Oversized spans become `#`, `##`, or `###` headings based on font clusters.
- Multi-column pages are read top-to-bottom within each column.
- Repeated running headers, footers, and page numbers are stripped.
- Embedded images are extracted to a sibling `.assets` directory.
- Image text is transcribed as `> *[Image Text]*: ...` captions.
- Pages with fewer than 50 extractable characters fall back to RapidOCR.
- `--no-ocr` disables OCR while retaining digital text and images.

## Sample fixture

`fixtures/sample.pdf` contains an inferred heading, body text, and an embedded
image.

```bash
uv run --script ../scripts/docmd fixtures/sample.pdf --stdout
```
