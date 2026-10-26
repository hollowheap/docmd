---
name: docmd
description: Convert DOCX, PPTX, and PDF documents into GitHub Flavored Markdown with extracted images, GFM tables, speaker notes, and offline OCR. Use when a document, deck, or paper must become readable Markdown.
license: MIT
compatibility: Requires `uv` to run the bundled PEP 723 script. OCR uses bundled CPU ONNX models and needs no system binaries.
metadata:
  version: "0.2.0"
---

# docmd

Convert Office documents and PDFs into GitHub Flavored Markdown.

## When to use

Use `docmd` when an agent or developer needs readable Markdown from `.docx`,
`.pptx`, or `.pdf` files, including extracted images, slide notes, and OCR text.

## Install

```bash
npx skills add <owner>/docmd --skill docmd
```

The skill ships one single-file PEP 723 script. `uv` runs it and resolves its
dependencies on first use.

## CLI

Paths are relative to this skill directory.

```bash
uv run --script scripts/docmd <input-path> [-o <out-path>] [--stdout]
      [--no-images] [--no-ocr] [--password <secret>] [--verify] [-j <n>]
      [-q] [-v] [-h]
```

- `--stdout` writes Markdown to standard output and inlines images as data URIs.
- File mode writes `<name>.md` next to a sibling `<name>.assets/` directory.
- Output normalizes smart quotes, dashes, ellipses, and invisible spaces to ASCII.
- `--jobs N` converts up to N documents concurrently for directory input
  (default: 2).
- `--verify` checks GFM table columns, code fences, and local asset links.
- Exit codes: `0` success, `1` CLI or runtime failure, `2` corrupt document,
  `3` encrypted document without a valid password.

## Consuming output

- Read headings, tables, and speaker notes directly as Markdown.
- Use `--stdout` for piped workflows; images are inlined as data URIs.
- Use `--verify` before downstream processing to catch broken tables, fences,
  or asset links.

## References

- `references/docx.md` — DOCX headings, lists, tables, images, and a sample.
- `references/pptx.md` — PPTX slides, speaker notes, tables, and a sample.
- `references/pdf.md` — PDF layout inference, OCR policy, and a sample.

Each guide ships a runnable sample under `references/fixtures/`.
