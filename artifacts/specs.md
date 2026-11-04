# Specs

### CLI & Runtime

#### System Shape

- [x] S01 [R01] [D01]: `skills/docmd/scripts/docmd` is a single-file PEP 723 executable; `uv run --script skills/docmd/scripts/docmd --version` prints a version and exits 0 without a pre-created virtualenv.
  - Verify: `uv run --script skills/docmd/scripts/docmd --version`
  - Seam: `scripts/docmd` PEP 723 metadata + `uv run --script`
  - Behavior: Prints a version and exits 0 without a pre-created virtualenv.
  - Failures: Missing or mismatched PEP 723 metadata prevents dependency resolution or execution.

- [x] S06 [R06] [D06]: CLI accepts an input path plus `-o/--out`, `--stdout`, `--no-images`, `--no-ocr`, `--password`, `--verify`, `-q/--quiet`, `-v/--version`, and `-h/--help`; missing input prints usage and fails.
  - Verify: `uv run pytest tests/test_cli.py::test_option_contract -q`
  - Seam: `build_parser` and `main`
  - Behavior: Accepts the documented options and prints usage plus a nonzero status when input is missing.
  - Failures: Usage and argument errors exit 1 instead of argparse's default 2.

- [x] S18 [R01] [D01]: PEP 723 `dependencies` in `scripts/docmd`, `pyproject.toml`, and `uv.lock` agree.
  - Verify: `uv run pytest tests/test_packaging.py::test_dependency_parity -q`
  - Seam: PEP 723 metadata, `pyproject.toml`, and `uv.lock`
  - Behavior: Keeps dependency declarations aligned, including the OpenCV pairing.
  - Failures: Parity test fails when manifests disagree.

- [x] S25 [R06] [D06]: `-o` is classified by `Path.suffix`: a suffix writes that exact file; no suffix creates the directory and writes `<stem>.md`.
  - Verify: `uv run pytest tests/test_cli.py::test_output_classification -q`
  - Seam: `main` output classification
  - Behavior: A suffix writes that exact file; no suffix creates the directory and writes `<stem>.md`.
  - Failures: Path classification mistakes can overwrite or misplace output.

#### Operations & Security

- [x] S07 [R07] [D07]: Process status is `0` on success, `1` on CLI or unhandled runtime failure, `2` on corrupt documents, and `3` on encrypted documents without a valid password.
  - Verify: `uv run pytest tests/test_exit_codes.py -q`
  - Seam: `exit_code_for` and `main`
  - Behavior: Maps success to 0, CLI/runtime failure to 1, corrupt documents to 2, and encrypted documents to 3.
  - Failures: Unclassified exceptions default to exit 1.

- [x] S28 [R06] [D06]: `--verify --stdout` validates data-URI Markdown and exits 1 on fence or table errors without writing files.
  - Verify: `uv run pytest tests/test_cli.py::test_stdout_verify -q`
  - Seam: `main` stdout path and `verify_markdown`
  - Behavior: Validates data-URI Markdown and exits 1 on fence or table errors without writing files.
  - Failures: Verification errors return exit 1.

- [x] S29 [R07] [D07]: Usage and argument errors print `usage:` plus an error to stderr and exit 1, never argparse's default 2.
  - Verify: `uv run pytest tests/test_exit_codes.py::test_usage_error_exit_one -q`
  - Seam: `DocmdArgumentParser` and `main`
  - Behavior: Usage and argument errors print `usage:` plus an error to stderr and exit 1.
  - Failures: Argparse's default exit 2 is overridden.

- [x] S30 [R07] [D07]: Unsupported file suffixes exit 1 with `unsupported input format` and write no output.
  - Verify: `uv run pytest tests/test_exit_codes.py::test_unsupported_extension -q`
  - Seam: `convert_document` and `main`
  - Behavior: Unsupported suffixes exit 1 with `unsupported input format` and write no output.
  - Failures: Unsupported input returns exit 1 before output creation.

### Document Parsing

#### Framework & Library Choices

- [x] S02 [R02] [D02]: `docmd sample.docx --stdout` emits ordered Markdown for paragraphs, heading styles, lists, inline images, and native tables, parsed with `python-docx`.
  - Verify: `uv run pytest tests/test_docx.py::test_block_extraction -q`
  - Seam: `convert_docx` via `python-docx`
  - Behavior: Emits paragraphs, heading styles, lists, inline images, and native tables in document order.
  - Failures: Corrupt or encrypted input raises and maps to exit 2 or 3.

- [x] S03 [R02] [D03]: `docmd sample.pptx --stdout` emits every slide in order with shape text, tables, and speaker notes, parsed with `python-pptx`.
  - Verify: `uv run pytest tests/test_pptx.py::test_slide_extraction -q`
  - Seam: `convert_pptx` via `python-pptx`
  - Behavior: Emits every slide in order with shape text, tables, and speaker notes.
  - Failures: Corrupt or encrypted input raises and maps to exit 2 or 3.

- [x] S04 [R02] [D04]: `docmd sample.pdf --stdout` preserves page text and uses PyMuPDF span font size and bounding boxes for layout inference.
  - Verify: `uv run pytest tests/test_pdf.py::test_span_extraction -q`
  - Seam: `extract_pdf_spans`/`convert_pdf` via PyMuPDF
  - Behavior: Preserves page text and exposes span font sizes and bounding boxes for layout inference.
  - Failures: Corrupt or encrypted PDF raises and maps to exit 2 or 3.

#### Data & Contracts

- [x] S10 [R02] [D10]: PPTX Markdown uses `## Slide <N>: <title>`, `---` between slides, and `> **Speaker Notes:** <content>` for notes.
  - Verify: `uv run pytest tests/test_pptx.py::test_markdown_layout -q`
  - Seam: `convert_pptx`
  - Behavior: Uses `## Slide <N>: <title>`, `---` separators, and `> **Speaker Notes:**` blocks.
  - Failures: Malformed slide content is still emitted as available text; conversion errors abort the document.

- [x] S11 [R02] [D10]: DOCX `Heading 1` through `Heading 6` map to `#` through `######`, and unstyled bold large-font paragraphs promote according to the document font hierarchy.
  - Verify: `uv run pytest tests/test_docx.py::test_heading_promotion -q`
  - Seam: `convert_docx` heading promotion
  - Behavior: Maps Heading 1-6 to Markdown headings and promotes bold oversized paragraphs by font hierarchy.
  - Failures: Unrecognized styles are treated as normal paragraphs.

- [x] S12 [R02] [D10]: PDF font-size clusters map oversized spans to `#`, `##`, and `###`; multi-column text sorts top-to-bottom within columns; repeated headers, footers, and page numbers are stripped.
  - Verify: `uv run pytest tests/test_pdf.py::test_pdf_layout -q`
  - Seam: `convert_pdf` layout inference
  - Behavior: Maps font-size clusters to headings, sorts multi-column text top-to-bottom, and strips repeated headers, footers, and page numbers.
  - Failures: Heuristic misclassification can alter heading levels but does not fail conversion.

- [x] S13 [R02] [D10]: Tables use strict GFM pipe syntax; merged cells flatten to regular rows and columns; internal cell newlines become `<br>`.
  - Verify: `uv run pytest tests/test_tables.py -q`
  - Seam: `markdown_table` and converter table handling
  - Behavior: Emits strict GFM pipe tables, flattens merged cells, and converts internal newlines to `<br>`.
  - Failures: Malformed table input is normalized rather than rejected; conversion errors abort the document.

- [x] S19 [R02] [D02]: DOCX `List Number` paragraphs emit `1. ` markers in document order; `List Bullet` paragraphs emit `- `.
  - Verify: `uv run pytest tests/test_docx.py::test_numbered_list_markers -q`
  - Seam: `convert_docx` list handling
  - Behavior: Emits `1. ` for List Number paragraphs and `- ` for List Bullet paragraphs in document order.
  - Failures: Unrecognized list styles are emitted as plain paragraphs.

- [x] S20 [R02] [D02]: DOCX paragraphs containing only a picture emit the image data URI and no empty text block.
  - Verify: `uv run pytest tests/test_docx.py::test_image_only_paragraph -q`
  - Seam: `convert_docx` image handling
  - Behavior: Image-only paragraphs emit the image data URI without an empty text block.
  - Failures: Missing image relations are skipped without aborting conversion.

- [x] S21 [R02] [D03]: PPTX picture shapes emit `data:<content-type>;base64,...`, falling back to extension-derived MIME and then `image/png`; undecodable pictures are skipped.
  - Verify: `uv run pytest tests/test_pptx_media.py::test_picture_mime -q`
  - Seam: `convert_pptx` picture handling
  - Behavior: Emits `data:<content-type>;base64,...` with extension and PNG fallbacks; undecodable pictures are skipped.
  - Failures: Undecodable picture shapes are skipped without aborting conversion.

- [x] S22 [R02] [D04]: PDF pages emit in document order and text from one page is not reordered across page boundaries.
  - Verify: `uv run pytest tests/test_pdf.py::test_page_order -q`
  - Seam: `convert_pdf` page iteration
  - Behavior: Emits pages in document order without cross-page text reordering.
  - Failures: Page extraction errors abort the document conversion.

- [x] S23 [R02] [D04]: Repeated PDF image references on a page emit one image block; invalid references are skipped without aborting the conversion.
  - Verify: `uv run pytest tests/test_pdf_media.py::test_xref_dedup -q`
  - Seam: `pdf_image_blocks`
  - Behavior: Emits repeated image references once and skips invalid references.
  - Failures: Invalid references are skipped without aborting conversion.

- [x] S34 [R02] [D10]: DOCX tables with zero rows emit no Markdown; PPTX tables with blank cells emit only a GFM header and separator.
  - Verify: `uv run pytest tests/test_tables.py::test_empty_tables -q`
  - Seam: `markdown_table` and converters
  - Behavior: DOCX zero-row tables emit no Markdown; PPTX blank-cell tables emit only a header and separator.
  - Failures: Empty table handling is format-specific.

- [x] S35 [R02] [D10]: PDF image links and captions emit after their page's text and before the next page's text.
  - Verify: `uv run pytest tests/test_pdf_media.py::test_image_page_order -q`
  - Seam: `convert_pdf` image entries
  - Behavior: Image links and captions emit after their page's text and before the next page's text.
  - Failures: Image block ordering depends on page extraction order.

### Media Extraction

#### Data & Contracts

- [x] S08 [R03] [D08]: File mode writes a sibling `<filename>.assets/` directory with relative links; `--stdout` inlines images as Base64 data URIs; `--no-images` omits all image Markdown.
  - Verify: `uv run pytest tests/test_media.py -q`
  - Seam: `write_markdown` and converter image blocks
  - Behavior: File mode writes sibling assets with relative links, stdout inlines Base64 data URIs, and `--no-images` omits image Markdown.
  - Failures: Asset directory or file write failures propagate as runtime errors.

- [x] S32 [R03] [D08]: File-mode assets are named `image-NNN.<ext>` in conversion order; unknown MIME types use `.bin`; unrelated existing files are preserved.
  - Verify: `uv run pytest tests/test_media.py::test_asset_naming -q`
  - Seam: `write_markdown`
  - Behavior: Names assets `image-NNN.<ext>` in conversion order, uses `.bin` for unknown MIME, and preserves unrelated files.
  - Failures: Asset write failures propagate as runtime errors.

- [x] S33 [R03] [D08]: Non-image or non-base64 data URIs remain inline and never create asset files.
  - Verify: `uv run pytest tests/test_media.py::test_non_image_data_uri -q`
  - Seam: `write_markdown` data-URI regex
  - Behavior: Non-image or non-base64 data URIs remain inline and never create asset files.
  - Failures: Malformed data URIs are left unchanged.

### Optical Character Recognition

#### Framework & Library Choices

- [x] S05 [R04] [D05]: OCR runs offline with bundled `rapidocr` and `openvino` PP-OCRv6 CPU models and requires no external system binaries.
  - Verify: `uv run pytest tests/test_ocr.py::test_offline_engine -q`
  - Seam: `load_ocr_engine` with RapidOCR/OpenVINO
  - Behavior: Runs offline with bundled PP-OCRv6 CPU models and needs no system binaries.
  - Failures: Missing OpenVINO/RapidOCR or model load failure aborts OCR with a runtime error.

#### Data & Contracts

- [x] S09 [R04] [D09]: PDF pages with fewer than 50 extractable characters trigger page OCR; embedded-image text appears as `> *[Image Text]*: ...` below the image; overlay reconciliation emits each text region once.
  - Verify: `uv run pytest tests/test_ocr_policy.py -q`
  - Seam: `convert_pdf`, `ocr_pdf_page`, `pdf_image_blocks`
  - Behavior: Pages with fewer than 50 extractable characters trigger OCR, image text becomes captions, and overlay regions emit once.
  - Failures: OCR or page-extraction failures can abort the document conversion.

- [x] S24 [R04] [D05]: OCR discards empty text and results with confidence below 0.5 before layout inference and caption emission.
  - Verify: `uv run pytest tests/test_ocr_policy.py::test_score_filter -q`
  - Seam: `ocr_items`, `ocr_pdf_page`, `ocr_image_text`
  - Behavior: Discards empty OCR text and results below 0.5 confidence before layout inference and captions.
  - Failures: Low-confidence or empty OCR results are dropped rather than emitted.

- [x] S27 [R04] [D09]: `--no-ocr` skips page fallback and image captions while retaining image links; `--no-images` removes links and captions.
  - Verify: `uv run pytest tests/test_ocr_policy.py::test_no_ocr_keeps_images -q`
  - Seam: `convert_pdf` and conversion options
  - Behavior: `--no-ocr` skips page fallback and captions while retaining image links; `--no-images` removes links and captions.
  - Failures: Incompatible option combinations follow the documented precedence.

- [x] S50 [R04] [D18]: `rapid-layout` PP-Structure model runs offline to detect layout blocks and order multi-column text lines into natural reading order.
  - Verify: `uv run pytest tests/test_ocr.py::test_offline_layout_engine tests/test_ocr.py::test_order_lines_by_layout -q`
  - Seam: `load_layout_engine`, `extract_layout_blocks`, `order_lines_by_layout`
  - Behavior: Runs offline with embedded PP-Structure ONNX model (~6.6 MB) to classify headers, titles, text blocks, and footers, sequencing multi-column lines without interleaving.
  - Failures: Missing model or engine failure gracefully falls back to geometric column ordering.

### Batch Processing

#### Module Seams

- [x] S14 [R05] [D11]: Directory input discovers non-hidden `.docx`, `.pptx`, and `.pdf` files recursively, mirrors subfolders under the output root, and co-locates each asset directory with its Markdown file.
  - Verify: `uv run pytest tests/test_batch.py -q`
  - Seam: `discover_documents` and `convert_directory`
  - Behavior: Discovers non-hidden supported files recursively, mirrors subfolders, and co-locates assets.
  - Failures: Discovery or per-document errors stop the batch and return the failing document's code.

- [x] S26 [R06] [D06]: Directory conversion logs each written Markdown path to stderr unless `-q/--quiet`; errors always print.
  - Verify: `uv run pytest tests/test_cli.py::test_quiet_progress -q`
  - Seam: `convert_directory` and `main`
  - Behavior: Logs each written Markdown path to stderr unless quiet; errors always print.
  - Failures: Suppressed progress can hide successful writes but errors remain visible.

- [x] S36 [R05] [D11]: Empty directory input exits 0, creates the output root, and discovery returns sorted deterministic paths.
  - Verify: `uv run pytest tests/test_batch.py::test_empty_input -q`
  - Seam: `discover_documents` and `convert_directory`
  - Behavior: Empty input exits 0, creates the output root, and discovery returns sorted deterministic paths.
  - Failures: Filesystem errors during discovery abort conversion.

- [x] S37 [R05] [D11]: Output roots nested under the input tree are excluded from discovery so generated Markdown is never reconverted.
  - Verify: `uv run pytest tests/test_batch.py::test_output_inside_input -q`
  - Seam: `discover_documents` exclusion
  - Behavior: Output roots nested under the input tree are excluded from discovery.
  - Failures: Misconfigured output roots can still be scanned if not excluded.

#### Operations & Security

- [x] S31 [R07] [D07]: Directory conversion aborts at the first failing document, returns that document's exit code, and leaves earlier outputs in place.
  - Verify: `uv run pytest tests/test_batch.py::test_partial_failure -q`
  - Seam: `convert_directory`
  - Behavior: Stops at the first failing document, returns its code, and leaves earlier outputs in place.
  - Failures: Later documents are not processed after a failure.

- [x] S49 [R05] [D17]: Directory conversion accepts `--jobs N` and defaults to 2; workers run with warm OCR engine and shared caption cache.
  - Verify: `uv run pytest tests/test_batch.py::test_parallel_jobs -q`
  - Seam: `convert_directory` and `OcrCache`
  - Behavior: Accepts `--jobs N` with default 2 and converts documents in parallel using warm workers sharing loaded models and OCR cache.
  - Failures: Invalid job counts exit 1 before conversion.

### Verification Mode

#### Operations & Security

- [x] S15 [R08] [D12]: `--verify` fails when a GFM table row column count differs from the header, a code fence is unbalanced, or a referenced local asset is missing or zero bytes.
  - Verify: `uv run pytest tests/test_verify.py -q`
  - Seam: `verify_markdown`
  - Behavior: Fails on table column mismatches, unbalanced fences, and missing or zero-byte local assets.
  - Failures: Verification returns an error list and the CLI exits 1.

- [x] S38 [R08] [D12]: `--verify` ignores anchor, `http(s)`, `mailto`, `data`, `file`, and protocol-relative links; URL-decodes local paths and strips query/fragment before checks.
  - Verify: `uv run pytest tests/test_verify.py::test_link_targets -q`
  - Seam: `verify_markdown` link handling
  - Behavior: Ignores anchor, http(s), mailto, data, file, and protocol-relative links; URL-decodes local paths and strips query/fragment.
  - Failures: Missing or zero-byte local assets are reported.

- [x] S39 [R08] [D12]: `--verify` treats `~~~` fences as code fences and reports unbalanced tilde fences.
  - Verify: `uv run pytest tests/test_verify.py::test_tilde_fences -q`
  - Seam: `fence_marker` and `verify_markdown`
  - Behavior: Treats `~~~` fences as code fences and reports unbalanced tilde fences.
  - Failures: Unbalanced fences return an error and exit 1.

- [x] S40 [R08] [D12]: Directory `--verify` checks each output against its own parent directory and returns exit 1 when any output fails; concurrent jobs may leave later outputs in place.
  - Verify: `uv run pytest tests/test_batch.py::test_verify_directory -q`
  - Seam: `convert_directory` with `--verify`
  - Behavior: Checks each output against its own parent directory and returns exit 1 when any output fails.
  - Failures: Concurrent jobs may leave later outputs in place after a failure.

### Skill Packaging

#### System Shape

- [x] S16 [R09] [D13]: `skills/docmd/` exposes `SKILL.md` with valid `name` and `description` frontmatter, executable `scripts/docmd`, `scripts/README.md`, format guides, and fixtures.
  - Verify: `uv run pytest tests/test_skill_layout.py -q`
  - Seam: `skills/docmd` tree and layout tests
  - Behavior: Exposes valid SKILL.md frontmatter, an executable script, README files, guides, and fixtures.
  - Failures: Missing or invalid skill files fail layout tests and the builder.

- [x] S44 [R09] [D15]: `skills/docmd/` holds the publishable tree: `SKILL.md` at the directory root, an executable `scripts/docmd` byte-identical to `scripts/docmd`, `README.md`, `scripts/README.md`, `references/{docx,pptx,pdf}.md`, and `references/fixtures/sample.{docx,pptx,pdf}`.
  - Verify: `uv run pytest tests/test_skill_layout.py -q`
  - Seam: `skills/docmd` publishable tree
  - Behavior: Holds SKILL.md at the root, a byte-identical executable script, README files, guides, and fixtures.
  - Failures: Missing or mismatched files fail layout tests.

#### Operations & Security

- [x] S17 [R09] [D14]: `scripts/dist.py` rebuilds `skills/docmd/` and converts each sample fixture through `skills/docmd/scripts/docmd`, asserting exit 0, non-empty Markdown, and expected asset creation.
  - Verify: `uv run python scripts/dist.py`
  - Seam: `scripts/dist.py`
  - Behavior: Rebuilds the skill tree and smoke-converts every sample fixture with exit 0 and non-empty Markdown.
  - Failures: Any build or smoke-conversion failure exits nonzero.

- [x] S42 [R09] [D14]: `scripts/dist.py` rejects missing static files or PEP 723 markers, exits nonzero, and leaves an existing packaged script untouched.
  - Verify: `uv run pytest tests/test_skill_builder.py::test_missing_source -q`
  - Seam: `scripts/dist.py` validation
  - Behavior: Rejects missing static files or PEP 723 markers, exits nonzero, and leaves an existing packaged script untouched.
  - Failures: Builder validation failures exit nonzero.

- [x] S43 [R09] [D14]: Repeated builder runs are byte-identical with mode `0o755` and mutate nothing outside `skills/docmd/` or temporary directories.
  - Verify: `uv run pytest tests/test_skill_builder.py::test_idempotent -q`
  - Seam: `scripts/dist.py` build determinism
  - Behavior: Repeated builds are byte-identical with mode 0o755 and mutate nothing outside the skill tree or temp dirs.
  - Failures: Nondeterministic filesystem state can fail the idempotence check.

- [x] S45 [R09] [D15]: `scripts/dist.py` syncs `scripts/docmd` into `skills/docmd/scripts/docmd` with mode `0o755` and fails with a nonzero exit when a static file, the PEP 723 metadata, or a SKILL.md frontmatter field is missing.
  - Verify: `uv run pytest tests/test_skill_builder.py -q`
  - Seam: `scripts/dist.py` sync
  - Behavior: Syncs the source script with mode 0o755 and fails when static files, PEP 723 metadata, or SKILL.md frontmatter are missing.
  - Failures: Builder validation failures exit nonzero.

- [x] S46 [R09] [D15]: `scripts/dist.py` smoke-converts every `skills/docmd/references/fixtures/sample.*` through the packaged script, asserting exit 0, non-empty Markdown, and extracted assets.
  - Verify: `uv run python scripts/dist.py`
  - Seam: `scripts/dist.py` smoke conversion
  - Behavior: Smoke-converts every fixture through the packaged script, asserting exit 0, non-empty Markdown, and extracted assets.
  - Failures: Any smoke-conversion failure exits nonzero.

#### Data & Contracts

- [x] S41 [R09] [D13]: Every `skills/docmd/reference/fixtures/sample.*` opens with its native parser, has a non-empty body, and contains media.
  - Verify: `uv run pytest tests/test_skill_layout.py::test_fixture_validity -q`
  - Seam: `skills/docmd/references/fixtures` and layout tests
  - Behavior: Every sample fixture opens with its native parser, has a non-empty body, and contains media.
  - Failures: Invalid fixtures fail layout tests.

- [x] S47 [R09] [D16]: `skills/docmd/SKILL.md` frontmatter declares `name: docmd` matching the directory, a non-empty description, `license: MIT`, a `compatibility` line naming `uv`, and `metadata.version`; the body links `references/docx.md`, `references/pptx.md`, and `references/pdf.md`.
  - Verify: `uv run pytest tests/test_skill_layout.py::test_frontmatter_contract -q`
  - Seam: `skills/docmd/SKILL.md` frontmatter
  - Behavior: Declares name, description, license, compatibility, and version, and links the three reference guides.
  - Failures: Invalid or missing frontmatter fails validation.

- [x] S48 [R09] [D16]: The repository ships an MIT `LICENSE` file and `skills/docmd/README.md` describing install, usage, and exit codes.
  - Verify: `uv run pytest tests/test_skill_layout.py::test_skill_and_readme -q`
  - Seam: Repository LICENSE and skill README
  - Behavior: Ships an MIT LICENSE and a README describing install, usage, and exit codes.
  - Failures: Missing documentation fails layout tests.
