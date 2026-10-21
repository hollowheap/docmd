# PPTX Reference

`docmd` converts PowerPoint decks into GitHub Flavored Markdown while keeping
slide order and speaker notes.

## Supported elements

- Each slide becomes `## Slide <N>: <title>`.
- Slides are separated with `---`.
- Shape text preserves paragraph order.
- Native PowerPoint tables become GFM tables.
- Speaker notes become `> **Speaker Notes:** <content>`.
- Slide images are extracted to a sibling `.assets` directory or inlined as
  Base64 data URIs with `--stdout`.

## Sample fixture

`fixtures/sample.pptx` contains a titled slide, body text, a table, an image,
and speaker notes.

```bash
uv run --script ../scripts/docmd fixtures/sample.pptx --stdout
```
