# Architecture

Last verified: 2026-11-04.
Scope: docmd document conversion CLI and skill packaging.

## System Shape

Zero-install Python CLI (`scripts/docmd`) executed via `uv run --script`.
Published skill tree under `skills/docmd/` with `SKILL.md`, references, and fixtures.
Distribution builder `scripts/dist.py` synchronizes `scripts/docmd` and smoke-tests fixtures.
Batch directory conversion executes in-process with a warm worker pool (`ThreadPoolExecutor`, `--jobs N`, defaulting to 2) sharing pre-loaded OCR models and a synchronized caption cache.
Process execution boundaries isolate secrets (passwords confined to environment/stdin, never command `argv`).

## Module Seams

- CLI Entrypoint (`main`): Argument parsing, path resolution, stdout pipe handling (`BrokenPipeError`), and exit code dispatch.
- Document Dispatch (`convert_source`, `convert_document`): Routes to format parsers with explicit error boundaries.
- Error Boundary Seam: `open_office_source` and `open_pdf` wrap corrupt file formats into `CorruptDocumentError`, while passing through `PermissionError`, `FileNotFoundError`, and `OSError` to preserve exit code 1.
- DOCX Parser (`convert_docx`): `python-docx` AST, heading promotion, tables, media, and cycle-safe style resolution.
- PPTX Parser (`convert_pptx`): `python-pptx` slides, shapes, notes text frames, tables, and media extraction.
- PDF Parser (`convert_pdf`): `pymupdf` single-handle lifecycle, spans, margins, layout blocks via `rapid-layout`, column ordering, layout inference, and safe image stream extraction.
- Layout Engine (`LayoutEngine`, `extract_layout_blocks`, `order_lines_by_layout`): PP-Structure ONNX model detects column blocks and restores multi-column reading order.
- OCR Pipeline (`load_ocr_engine`, `ocr_image_text`, `ocr_pdf_page`): OpenVINO PP-OCRv6 inference with model accelerator pre-warming, layout suppression, and NaN score filtering.
- Markdown Writer (`write_markdown`): Asset directory creation, image extraction, and relative link generation with rollback on verification failure.
- Verifier (`verify_markdown`): Markdown table column counts (pipe-in-code masking), code fence balancing, and asset link validation contained within output directory root.
- Batch Engine (`convert_directory`): In-process worker pool (`ThreadPoolExecutor`) sharing pre-loaded `ocr_engine` and thread-safe `OcrCache`.

## Dependency Direction

- `main` parses CLI options and dispatches to `convert_directory` for directories or `convert_source` for single files.
- `convert_source` -> `convert_document` -> `convert_docx` / `convert_pptx` / `convert_pdf`.
- `convert_pdf` -> `extract_pdf_lines`, `strip_pdf_margins`, `pdf_image_blocks`, layout helpers (`extract_layout_blocks`, `order_lines_by_layout`), and OCR helpers (`ocr_pdf_page`, `ocr_image_text`) using `load_ocr_engine`.
- `convert_docx` and `convert_pptx` -> `open_office_source`.
- `convert_one` -> `convert_source` then `write_markdown`.
- `convert_directory` orchestrates workers and calls `convert_one` directly in-process with shared `ocr_engine` and `OcrCache`.
- `verify_markdown` and `write_markdown` are leaf utilities consumed by `main`, `convert_one`, and tests.
- `tests/` import `scripts.docmd` as a module; production code does not import tests.

## Framework & Library Choices

- `python-docx==1.2.0`: Native OOXML `.docx` style and table traversal.
- `python-pptx==1.0.2`: Native OOXML `.pptx` slide, shape, and note traversal.
- `pymupdf==2.0`: High-performance memory-mapped PDF layout and text span extraction with single-handle lifecycle.
- `rapidocr==3.10.0` with `openvino==2026.4.1`: Fast CPU inference with PP-OCRv6 models; accelerator compilation hooked during model initialization.
- `rapid-layout==1.2.1`: PP-Structure ONNX model for layout block detection and multi-column reading order.
- `opencv-python-headless==5.0.0.93`: Image decoding without GUI dependencies.
- `msoffcrypto-tool==6.0.0`: Encrypted document detection and in-memory decryption.
- `tool.uv.override-dependencies`: `opencv-python ; sys_platform == 'never'` guarantees headless OpenCV across all dependencies.

## Data & Contracts

- Input: `.docx`, `.pptx`, `.pdf` files or recursive directory trees.
- Output: GitHub Flavored Markdown (GFM) with UTF-8 encoding.
- Media Seam: Base64 data URIs inline for `--stdout`; sibling `<stem>.assets/image-NNN.<ext>` for file output.
- Link Contract: Local links validated within directory tree; non-ASCII and parenthesized filenames preserved.
- Table Contract: Table cell parsing ignores pipes embedded within inline backtick code spans.
- Exit Codes: `0` (success), `1` (CLI/runtime failure or unreadable file), `2` (corrupt input structure/stream), `3` (encrypted input without password).

## Operations & Security

- Warm worker thread pool for directory batch conversion (`--jobs N`, default 2) sharing pre-loaded OCR models and thread-safe caption cache (`OcrCache` bounded at 1000 items).
- Secret confinement: document passwords kept in memory within worker options, preventing `/proc/<pid>/cmdline` exposure.
- Verification containment: local asset validation sandboxed to output directory root (`is_relative_to`), preventing filesystem probing.
- Safe pipe handling: stdout streaming exits gracefully on `BrokenPipeError` without stack traces.
- No remote telemetry, no external network calls during conversion.

## Known Debt

- Multi-column PDF layout: PP-Structure ONNX resolves column ordering; nested non-standard table layouts within columns still rely on cell heuristics.
- DOCX style cycles: circular `w:basedOn` style inheritance requires cycle-detection guard.
- PPTX grouped shapes: `MSO_SHAPE_TYPE.GROUP` shapes require recursive traversal to extract nested content.
- Same-stem collisions: identical stems across different formats in the same directory (`sample.docx`, `sample.pdf`) collide on `<stem>.md` and `<stem>.assets/`.
- RapidOCR / OpenVINO initialization adds latency on first OCR invocation.

## Evidence

- Robustness reviews V01–V05 in `artifacts/reviews.md` and `artifacts/review/*.md`.
- Settled decisions D01–D18 in `artifacts/decisions.md`.
- Formal specifications S01–S50 in `artifacts/specs.md`.
- Automated test suite `tests/` covering exit codes, media extraction, layout, batch processing, and verification.
