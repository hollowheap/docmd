# Requirements

### CLI & Runtime

- [x] R01: Provide zero-install command-line execution for single documents producing Markdown.
  - Verify: `uv run --script scripts/docmd --version`
  - Acceptance: A supported input converts without a pre-created virtualenv and emits Markdown.
  - Constraints: Zero-install execution without prior environment setup.
  - Non-goals: Interactive document viewer or GUI.
  - Rationale: Enables agents and automated scripts to run conversions instantly.

### Document Parsing

- [x] R02: Preserve document hierarchy, reading order, and layout semantics when converting Office and PDF documents.
  - Verify: `uv run pytest tests/test_docx.py tests/test_pptx.py tests/test_pdf.py -q`
  - Acceptance: Headings, lists, tables, slides, columns, and running headers or footers are represented faithfully.
  - Constraints: Format-specific parsing preserves hierarchy and reading order without cross-page reordering.
  - Non-goals: Pixel-perfect visual rendering.
  - Rationale: Downstream LLM tools require clean, structured reading order.

### Media Extraction

- [x] R03: Extract embedded images and represent them as Markdown images in file and stdout modes.
  - Verify: `uv run pytest tests/test_media.py -q`
  - Acceptance: Images become relative asset links or Base64 data URIs, and `--no-images` omits them.
  - Constraints: Media handling follows one extraction seam for all formats.
  - Non-goals: Image transformation, filtering, or resizing.
  - Rationale: Retains visual information without breaking terminal or file usage.

### Optical Character Recognition

- [x] R04: Recover text from scanned pages and embedded images using offline OCR.
  - Verify: `uv run pytest tests/test_ocr.py tests/test_ocr_policy.py -q`
  - Acceptance: Low-text pages OCR, image captions appear, and overlay text is not duplicated.
  - Constraints: OCR runs without external binaries or network services.
  - Non-goals: Full document layout retraining or handwriting recognition.
  - Rationale: Extracts textual knowledge trapped inside scans and embedded diagrams.

### Batch Processing

- [x] R05: Convert directories of supported documents recursively with deterministic output layout.
  - Verify: `uv run pytest tests/test_batch.py -q`
  - Acceptance: Subfolders mirror, assets co-locate, discovery is deterministic, and nested outputs are skipped.
  - Constraints: Batch conversion scales with warm in-process workers.
  - Non-goals: In-place file modification.
  - Rationale: Facilitates batch ingestion of large document corpora.

### CLI Contract

- [x] R06: Provide a stable CLI with options, output classification, progress logging, and usage errors.
  - Verify: `uv run pytest tests/test_cli.py -q`
  - Acceptance: Options parse as documented and usage errors exit 1.
  - Constraints: CLI contract stays stable for agents and scripts.
  - Non-goals: Interactive configuration wizard.
  - Rationale: Predictable CLI contract for automated agent harnesses.

### Error Handling

- [x] R07: Report machine-actionable exit codes for success, runtime failure, corrupt documents, and encrypted documents.
  - Verify: `uv run pytest tests/test_exit_codes.py -q`
  - Acceptance: Exit codes are 0, 1, 2, and 3 as documented.
  - Constraints: Discrete exit codes for each major failure condition.
  - Non-goals: Interactive password prompts.
  - Rationale: Callers need programmatic classification of failure causes.

### Verification Mode

- [x] R08: Validate generated Markdown for table alignment, fence balance, and asset integrity.
  - Verify: `uv run pytest tests/test_verify.py -q`
  - Acceptance: `--verify` fails on malformed tables, unbalanced fences, and bad assets.
  - Constraints: Verification catches broken output before downstream use.
  - Non-goals: Full CommonMark specification compliance test suite.
  - Rationale: Prevents distribution or consumption of damaged Markdown.

### Skill Packaging

- [x] R09: Distribute docmd as a versioned skill with a reproducible builder.
  - Verify: `uv run python scripts/dist.py`
  - Acceptance: Packaged tree is byte-identical, executable, and smoke-converts fixtures.
  - Constraints: Skill packaging avoids drift between source and published tree.
  - Non-goals: Distribution via external package indices (PyPI).
  - Rationale: Ensures skills.sh and agent harnesses can discover and execute docmd reliably.
