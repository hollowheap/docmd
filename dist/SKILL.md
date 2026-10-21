---
name: docmd
description: Converts Office documents (PPTX, DOCX) and PDFs into clean, structured GitHub Flavored Markdown with automatic image extraction, slide delimitation, and hybrid OCR.
---

# docmd

Convert Office documents and PDFs into GitHub Flavored Markdown.

## When to use

Use `docmd` when an agent or developer needs readable Markdown from `.docx`,
`.pptx`, or `.pdf` files, including extracted images, slide notes, and OCR text.

## CLI

```bash
docmd <input-path> [-o <out-path>] [--stdout] [--no-images] [--no-ocr]
      [--password <secret>] [--verify] [-q] [-v] [-h]
```

## Consuming output

- Read headings, tables, and speaker notes directly as Markdown.
- Use `--stdout` for piped workflows; images are inlined as data URIs.
- Use `--verify` before downstream processing to catch broken tables, fences,
  or asset links.
