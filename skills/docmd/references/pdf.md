# PDF Reference

`docmd` converts PDFs into GitHub Flavored Markdown using font size, bounding
boxes, and optional offline OCR.

## Supported elements

- Oversized spans become `#`, `##`, or `###` headings based on font clusters;
  headings are limited to twelve words and never come from OCR fragments.
- `rapid-layout` block detection orders multi-column pages; geometric x-cluster
  ordering is the logged fallback when the layout model is unavailable.
- Paragraph gaps, bullet lists, dehyphenation, and aligned text tables are
  recovered before Markdown is emitted.
- Link annotations become Markdown links, and repeated running headers,
  footers, and page numbers are stripped.
- Embedded images are extracted to a sibling `.assets` directory.
- Image text is transcribed as `> *[Image Text]*: ...` captions and suppressed
  when it duplicates the page body.
- Pages with fewer than 50 extractable characters, or with a dominant image
  covering more than 60 percent of the page, run RapidOCR. OCR lines matching
  digital text are discarded, so digital text and its font size win.
- `--no-ocr` disables OCR while retaining digital text and images.
- A PDF with no extractable text or images exits `2`.

## Sample fixture

`fixtures/sample.pdf` contains an inferred heading, body text, and an embedded
image.

```bash
uv run --script ../scripts/docmd fixtures/sample.pdf --stdout
```
