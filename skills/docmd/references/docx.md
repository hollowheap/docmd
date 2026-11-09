# DOCX Reference

`docmd` converts Word documents into GitHub Flavored Markdown with native
paragraph, heading, list, table, and image handling.

## Supported elements

- Heading styles 1 through 6 map to `#` through `######`.
- Large bold runs are promoted to headings when they exceed the body text size.
- Paragraphs preserve document order and run-level bold, italic, strikethrough,
  monospace, and hyperlinks.
- Bullet and numbered lists become Markdown list items; numbering levels come
  from `numbering.xml` when present and counters increment within a list.
- Native Word tables become GFM tables; merged cells appear once and are
  flattened to empty cells.
- Inline images, including images inside table cells, are extracted to a
  sibling `.assets` directory or inlined as Base64 data URIs with `--stdout`.
- Footnote and endnote references become `[^n]` markers with definitions at
  the end of the Markdown.

## Sample fixture

`fixtures/sample.docx` contains a heading, paragraph, table, bullet list, and
image.

```bash
uv run --script ../scripts/docmd fixtures/sample.docx --stdout
```
