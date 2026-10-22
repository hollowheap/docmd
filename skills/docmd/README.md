# docmd

Convert DOCX, PPTX, and PDF documents into GitHub Flavored Markdown.

## What you get

- One single-file PEP 723 script (`scripts/docmd`) that runs under `uv`.
- Headings, lists, GFM tables, speaker notes, and extracted images.
- Offline OCR for scanned pages and text inside embedded images.
- ASCII-normalized typography: smart quotes, dashes, ellipses, and invisible spaces.
- `--verify` to catch broken tables, code fences, and asset links before use.

## Install

```bash
npx skills add <owner>/docmd --skill docmd
```

## Usage

```bash
uv run --script scripts/docmd report.pdf --stdout
uv run --script scripts/docmd report.pdf -o ./out --verify
uv run --script scripts/docmd ./documents -o ./out
```

- `--stdout` prints Markdown and inlines images as Base64 data URIs.
- File mode writes `<name>.md` plus a sibling `<name>.assets/` directory.
- `--no-ocr` skips OCR, `--no-images` skips image extraction.
- Exit codes: `0` success, `1` CLI or runtime failure, `2` corrupt document,
  `3` encrypted document without a valid password.

## Reference

- `references/docx.md`, `references/pptx.md`, `references/pdf.md` — per-format
  behavior and runnable samples in `references/fixtures/`.

## License

MIT — see the `LICENSE` file at the repository root.
