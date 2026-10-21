# DOCX Reference

`docmd` converts Word documents into GitHub Flavored Markdown with native
paragraph, heading, list, table, and image handling.

## Supported elements

- Heading styles 1 through 6 map to `#` through `######`.
- Large bold runs are promoted to headings when they exceed the body text size.
- Paragraphs preserve document order.
- Bullet and numbered lists become Markdown list items.
- Native Word tables become GFM tables with merged cells flattened.
- Inline images are extracted to a sibling `.assets` directory or inlined as
  Base64 data URIs with `--stdout`.

## Sample fixture

`fixtures/sample.docx` contains a heading, paragraph, table, bullet list, and
image.

```bash
uv run --script ../scripts/docmd fixtures/sample.docx --stdout
```
