# Requirements

- [x] R01: Run docmd as a zero-install command-line tool on a single supported document and produce Markdown.
  - Verify: `uv run --script scripts/docmd --version`
  - Acceptance: A supported input converts without a pre-created virtualenv and emits Markdown.
  - Runs as a PEP 723 script under uv so dependencies resolve on demand.

- [x] R02: Preserve document structure, reading order, and layout semantics when converting DOCX, PPTX, and PDF files.
  - Verify: `uv run pytest tests/test_docx.py tests/test_pptx.py tests/test_pdf.py -q`
  - Acceptance: Headings, lists, tables, slides, columns, and running headers or footers are represented faithfully.
  - Format-specific parsing preserves hierarchy and reading order.

- [x] R03: Extract embedded images and represent them as Markdown images in file and stdout modes.
  - Verify: `uv run pytest tests/test_media.py -q`
  - Acceptance: Images become relative asset links or Base64 data URIs, and `--no-images` omits them.
  - Media handling follows one extraction seam for all formats.

- [x] R04: Recover text from scanned pages and embedded images using offline OCR.
  - Verify: `uv run pytest tests/test_ocr.py tests/test_ocr_policy.py -q`
  - Acceptance: Low-text pages OCR, image captions appear, and overlay text is not duplicated.
  - OCR runs without external binaries.

- [x] R05: Convert directories of supported documents recursively with deterministic output layout.
  - Verify: `uv run pytest tests/test_batch.py -q`
  - Acceptance: Subfolders mirror, assets co-locate, discovery is deterministic, and nested outputs are skipped.
  - Batch conversion scales with isolated workers.

- [x] R06: Provide a stable CLI with options, output classification, progress logging, and usage errors.
  - Verify: `uv run pytest tests/test_cli.py -q`
  - Acceptance: Options parse as documented and usage errors exit 1.
  - CLI contract stays stable for agents and scripts.

- [x] R07: Report machine-actionable exit codes for success, runtime failure, corrupt documents, and encrypted documents.
  - Verify: `uv run pytest tests/test_exit_codes.py -q`
  - Acceptance: Exit codes are 0, 1, 2, and 3 as documented.
  - Failure classes are distinguishable by status code.

- [x] R08: Validate generated Markdown for table alignment, fence balance, and asset integrity.
  - Verify: `uv run pytest tests/test_verify.py -q`
  - Acceptance: `--verify` fails on malformed tables, unbalanced fences, and bad assets.
  - Verification catches broken output before downstream use.

- [x] R09: Distribute docmd as a versioned skill with a reproducible builder.
  - Verify: `uv run python scripts/dist.py`
  - Acceptance: Packaged tree is byte-identical, executable, and smoke-converts fixtures.
  - Skill packaging avoids drift between source and published tree.
