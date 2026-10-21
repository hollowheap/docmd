# Decisions

- [x] D01: Ship `docmd` as a Python 3.11+ single-file PEP 723 CLI run with `uv` | Why: zero-install execution mirrors md-questioner and avoids environment drift
- [x] D02: Use `python-docx` for `.docx` parsing | Why: native access to styles, tables, and embedded media
- [x] D03: Use `python-pptx` for `.pptx` parsing | Why: native access to slides, shapes, speaker notes, and media
- [x] D04: Use `pymupdf` (`fitz`) for `.pdf` parsing | Why: one dependency covers layout, text spans, fonts, and image streams
- [x] D05: Use `rapidocr-onnxruntime` for OCR | Why: bundled CPU ONNX models run offline without system binaries such as tesseract
- [x] D06: CLI accepts an input path plus `-o/--out`, `--stdout`, `--no-images`, `--no-ocr`, `--password`, `--verify`, `-q/--quiet`, `-v/--version`, and `-h/--help` | Why: stable interface for agents and scripts
- [x] D07: Exit `0` on success, `1` on CLI/runtime failure, `2` on corrupt documents, and `3` on encrypted documents without a valid password | Why: machine-actionable failure classes
- [x] D08: File mode writes a sibling `<filename>.assets/` directory with relative links; `--stdout` inlines images as Base64 data URIs; `--no-images` omits image syntax | Why: avoid orphan files in pipes while keeping file-mode asset links predictable
- [x] D09: OCR runs on PDF pages with fewer than 50 extractable characters, transcribes embedded images into blockquote captions, and reconciles OCR against digital text | Why: recover scanned and diagram text without duplicating searchable content
- [x] D10: Apply format-specific layout rules for PPTX slide headings and notes, DOCX heading styles and font promotion, PDF font-cluster headings, multi-column order, running header/footer suppression, and GFM tables | Why: preserve document hierarchy and reading order
- [x] D11: Directory input recurses through non-hidden `.docx`, `.pptx`, and `.pdf` files and mirrors the input hierarchy in the output tree | Why: predictable batch conversion
- [x] D12: `--verify` checks GFM table column alignment, balanced code fences, and resolvable non-empty asset links | Why: catch broken Markdown before downstream use
- [x] D13: `dist/` contains `SKILL.md`, `scripts/docmd`, `scripts/README.md`, reference guides, and fixtures | Why: md-questioner-compatible skill distribution
- [x] D14: `scripts/dist.py` builds the distribution and runs smoke conversions on sample fixtures | Why: verify the packaged artifact before distribution

## Non-Goals

- None recorded.
