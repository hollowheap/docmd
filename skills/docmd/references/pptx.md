# PPTX Reference

`docmd` converts PowerPoint decks into GitHub Flavored Markdown while keeping
slide order and speaker notes.

## Supported elements

- Each slide becomes `## Slide <N>: <title>`.
- Slides are separated with `---`.
- Shapes are read in visual order: vertical bands, then left to right.
- Text frames preserve bullet paragraphs, indentation levels, and run-level
  bold, italic, and monospace.
- Native PowerPoint tables become GFM tables; charts become a small category
  and series table, and SmartArt contributes its text nodes.
- Unreadable shape classes emit an HTML comment naming the shape and slide
  instead of disappearing silently.
- Speaker notes become `> **Speaker Notes:** <content>` with every note line
  kept inside the blockquote.
- Slide images are extracted to a sibling `.assets` directory or inlined as
  Base64 data URIs with `--stdout`.

## Sample fixture

`fixtures/sample.pptx` contains a titled slide, body text, a table, an image,
and speaker notes.

```bash
uv run --script ../scripts/docmd fixtures/sample.pptx --stdout
```
