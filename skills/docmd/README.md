# docmd

Convert DOCX, PPTX, and PDF documents into GitHub Flavored Markdown.

## What you get

- One single-file PEP 723 script (`scripts/docmd`) that runs under `uv`.
- Headings, lists, GFM tables, speaker notes, and extracted images.
- Offline OCR for scanned pages and text inside embedded images, merged against digital text.
- Typography normalisation: smart quotes, dashes, ellipses, and invisible spaces; code and link destinations are left untouched.
- `--verify` to catch broken tables, code fences, and inline, reference, or HTML asset links before use.

## Install

```bash
npx skills@1.7.4 add hollowheap/docmd --skill docmd
```

## Usage

```bash
uv run --script scripts/docmd report.pdf --stdout
uv run --script scripts/docmd report.pdf -o ./out --verify
uv run --script scripts/docmd ./documents -o ./out
```

- `--stdout` prints Markdown and inlines images as Base64 data URIs.
- File mode writes `<name>.md` plus a sibling `<name>.assets/` directory.
- `--no-ocr` skips OCR, `--no-images` skips image extraction, and
  `--no-sanitize` leaves typography unchanged.
- `--jobs N` converts up to N directory documents concurrently (default: 2).
  A failed batch publishes only documents before the first failure in sorted
  order.
- `DOCMD_PASSWORD` is the preferred way to supply an encrypted document
  password; `--password` remains available but exposes the secret in argv.
- Exit codes: `0` success, `1` CLI or runtime failure, `2` corrupt document,
  `3` encrypted document without a valid password.
- OCR env: `DOCMD_OCR_DEVICE=cpu|gpu|npu|auto` (default `auto`),
  `DOCMD_OCR_MODEL=tiny|small` (default `tiny`),
  `DOCMD_OCR_THREADS=N` (default `min(4, cpu_count)`), and
  `DOCMD_OCR_CONFIDENCE=0.0..1.0` (default `0.5`). Invalid values abort with
  exit `1`.

## Reference

- `references/docx.md`, `references/pptx.md`, `references/pdf.md` — per-format
  behavior and runnable samples in `references/fixtures/`.

## License

MIT — see the `LICENSE` file at the repository root.
