# Decisions

### System Shape

- [x] D01 [R01]: Ship `docmd` as a Python 3.11+ single-file PEP 723 CLI run with `uv`
  - Context: Zero-install execution avoids environment drift and setup friction for agents.
  - Alternatives: Traditional wheel packaging on PyPI (rejected due to publishing overhead).
  - Consequences: Relies on `uv` to manage isolated execution environments.
  - Resolves: Q01

- [x] D06 [R06]: CLI accepts an input path plus `-o/--out`, `--stdout`, `--no-images`, `--no-ocr`, `--password`, `--verify`, `-q/--quiet`, `-v/--version`, and `-h/--help`
  - Context: Stable CLI contract needed by both automated agents and human users.
  - Alternatives: Interactive prompts or subcommand structure (rejected as overly complex).
  - Consequences: Single binary interface parses all options uniformly.

- [x] D13 [R09]: `skills/docmd/` contains `SKILL.md`, `scripts/docmd`, `scripts/README.md`, reference guides, and fixtures
  - Context: Skill distribution requires standard layout for discovery by skills.sh.
  - Alternatives: Independent repository for skill (rejected to avoid monorepo drift).
  - Consequences: Packaged skill tree must mirror script source of truth.

- [x] D15 [R09]: Publish the skill from this repository as a monorepo skill at `skills/docmd/`, installed with `npx skills add <owner>/<repo> --skill docmd`; `scripts/docmd` stays the source of truth and `scripts/dist.py` syncs it into the published tree
  - Context: skills.sh indexes public GitHub repos without an upload registry step.
  - Alternatives: Manual copy-paste into skill directories (rejected as prone to drift).
  - Consequences: Automated sync script needed to ensure parity.

### Module Seams

- [x] D11 [R05]: Directory input recurses through non-hidden `.docx`, `.pptx`, and `.pdf` files and mirrors the input hierarchy in the output tree
  - Context: Batch processing must retain directory structures predictably.
  - Alternatives: Flattening all outputs into a single directory (rejected due to collisions).
  - Consequences: Output directory tree mirrors input folder structure.

### Framework & Library Choices

- [x] D02 [R02]: Use `python-docx` for `.docx` parsing
  - Context: Need native access to styles, tables, and embedded media in Word documents.
  - Alternatives: Pandoc or mammoth (rejected due to external binaries and loss of styling).
  - Consequences: Direct OOXML parsing preserves style hierarchy.

- [x] D03 [R02]: Use `python-pptx` for `.pptx` parsing
  - Context: Need native access to slides, shapes, speaker notes, and media.
  - Alternatives: LibreOffice headless conversion (rejected due to heavy system runtime).
  - Consequences: Reliable slide and note extraction in pure Python.

- [x] D04 [R02]: Use `pymupdf` (`fitz`) for `.pdf` parsing
  - Context: One fast dependency needed for PDF layout, text spans, fonts, and image streams.
  - Alternatives: pypdf, pdfplumber (rejected due to lower extraction speed and precision).
  - Consequences: High performance C-backed PDF parsing.

- [x] D05 [R04]: Use `rapidocr` and `openvino` with PP-OCRv6 models for offline OCR
  - Context: CPU OCR must run offline without requiring external system binaries like tesseract.
  - Alternatives: Tesseract OCR (rejected for external binary dependencies), ONNX Runtime (superseded by OpenVINO PP-OCRv6 for speed).
  - Consequences: Fast CPU inference with bundled models; first run initialization overhead.
  - Resolves: Q02

### Data & Contracts

- [x] D08 [R03]: File mode writes a sibling `<filename>.assets/` directory with relative links; `--stdout` inlines images as Base64 data URIs; `--no-images` omits image syntax
  - Context: Downstream markdown consumers need clear separation between file assets and streams.
  - Alternatives: Always using data URIs (rejected for massive file sizes) or always writing files (rejected for stdout pipes).
  - Consequences: Dual-mode media handling based on destination.

- [x] D09 [R04]: OCR runs on PDF pages with fewer than 50 extractable characters, transcribes embedded images into blockquote captions, and reconciles OCR against digital text
  - Context: Scanned pages and embedded diagrams contain text that digital extraction misses.
  - Alternatives: Running OCR unconditionally on every page (rejected for severe performance hit).
  - Consequences: Fallback OCR triggers only when digital text density is low.

- [x] D10 [R02]: Apply format-specific layout rules for PPTX slide headings and notes, DOCX heading styles and font promotion, PDF font-cluster headings, multi-column order, running header/footer suppression, and GFM tables
  - Context: Document formats have distinct semantic layouts that must map cleanly to Markdown.
  - Alternatives: Generic unformatted text dumping (rejected for losing document structure).
  - Consequences: Tailored layout heuristics for each supported format.

- [x] D16 [R09]: Ship the skill under MIT with `SKILL.md` frontmatter carrying `name`, `description`, `license`, `compatibility`, and `metadata.version`, and link the three reference guides from `SKILL.md`
  - Context: Standard skill metadata required by agents and skills.sh discovery.
  - Alternatives: Unversioned or incomplete frontmatter (rejected by validation checks).
  - Consequences: Frontmatter contract strictly validated during distribution build.

### Operations & Security

- [x] D07 [R07]: Exit `0` on success, `1` on CLI/runtime failure, `2` on corrupt documents, and `3` on encrypted documents without a valid password
  - Context: Calling agents and scripts need actionable machine exit codes to differentiate error types.
  - Alternatives: Generic non-zero exit 1 for all failures (rejected for poor automation ergonomics).
  - Consequences: Exit codes explicitly classified across all modules.

- [x] D12 [R08]: `--verify` checks GFM table column alignment, balanced code fences, and resolvable non-empty asset links
  - Context: Markdown corruption or broken asset links should be caught prior to downstream use.
  - Alternatives: Relying solely on downstream renderer error reporting (rejected for silent breakage).
  - Consequences: Self-verifying CLI flags ensure output integrity.

- [x] D14 [R09]: `scripts/dist.py` builds the distribution and runs smoke conversions on sample fixtures
  - Context: Verification step needed before publishing to catch broken dependencies or syntax.
  - Alternatives: Manual testing before release (rejected as error-prone).
  - Consequences: Automated smoke test suite validates packaged skill artifacts.

- [x] D17 [R05]: Convert directory documents using warm in-process worker pool (`--jobs N`, defaulting to 2) with synchronized OCR engine and caption cache
  - Context: Batch conversion with isolated subprocesses incurred 1.5-3.0s cold startup and OpenVINO model compilation per document, preventing cross-document image deduplication.
  - Alternatives: Cold subprocess per document (rejected due to repeated model compile and empty cache per file); uncoordinated shared state (rejected for thread safety).
  - Consequences: Thread-safe `OcrEngine` and synchronized `OcrCache` share loaded models and OCR digests across workers, eliminating duplicate inference while scaling across CPU cores.

- [x] D18 [R04]: Use `rapid-layout` (PP-Structure ONNX) with recursive column clustering to classify layout blocks and restore multi-column reading order
  - Context: Multi-column documents and dense screenshot images interleave text when sorted naively by coordinate; autoregressive VLMs (Surya/Qwen) were evaluated and rejected for high latency (50-80s), GPU dependency, and repetition loops.
  - Alternatives: Autoregressive VLM (rejected for 100x latency and hallucination loops); heuristic-only sorting (rejected for collapsing across full-width banners).
  - Consequences: Lightweight PP-Structure model (~6.6 MB ONNX) runs offline in <0.4s on CPU with zero API keys; headless OpenCV enforced via `[tool.uv.override-dependencies]`.

### Corrective Pass (2026-11-09)

- [x] D19 [R04]: Digital PDF text is the ground truth; OCR fills gaps and never replaces a page's digital lines
  - Context: OCR replacement changed trustworthy page numbers, headers, and heading sizes on pages with a text layer.
  - Alternatives: OCR-first pages (rejected for backend-sensitive output); OCR-only on scanned pages (kept as the no-digital-text case).
  - Consequences: OCR lines matching digital lines are dropped, margin stripping runs after the merge, and OCR fragments never become headings.

- [x] D20 [R02]: PDF structure recovery uses layout blocks with a logged geometric fallback, then paragraph gaps, lists, aligned text tables, dehyphenation, and link annotations
  - Context: `rapid-layout` was only used for image captions, so PDF pages flattened to one prose paragraph per page.
  - Alternatives: Layout-only ordering (rejected when the model is unavailable); geometric-only ordering (rejected for multi-column pages).
  - Consequences: The layout engine loads once per PDF; failures log a fallback line instead of failing the conversion.

- [x] D21 [R08]: `--verify` checks single- and multi-column tables, quoted tables, inline and reference links, and HTML image sources, and reports its counts
  - Context: The previous checker missed single-column tables, reference definitions, HTML images, and tables inside blockquotes.
  - Alternatives: Narrowing the documented claim (rejected because verification is the downstream gate).
  - Consequences: Passing runs log the number of fences, tables, links, and images checked.

- [x] D22 [R05]: Directory conversion stages every document, then commits staged outputs in sorted document order and stops at the first failure
  - Context: `as_completed` returned whichever failure finished first and running workers kept publishing after the batch failed.
  - Alternatives: Killing running workers (rejected; in-process workers cannot be terminated safely); restoring subprocess isolation (rejected for OCR cache and startup cost).
  - Consequences: Batch exit codes are deterministic and only documents before the first failing document are published.

- [x] D23 [R01]: Typography normalisation applies only to prose, is named honestly, and can be disabled with `--no-sanitize`
  - Context: The old ASCII pass rewrote chemical formulae, superscripts, arrows, multiplication signs, URLs, and code.
  - Alternatives: Keeping the lossy default (rejected); normalising code and destinations (rejected).
  - Consequences: Smart quotes, dashes, ellipses, and invisible spaces are normalised in prose; code spans, fences, link destinations, and mathematical symbols survive.

- [x] D24 [R07]: Resource budgets and empty-conversion handling are explicit runtime contracts
  - Context: Untrusted documents could exhaust memory, and a PDF with no text or images exited successfully with empty Markdown.
  - Alternatives: No limits (rejected for agent-facing conversion); a new exit code for empty output (rejected to preserve the four-value contract).
  - Consequences: Byte, page, and image-pixel budgets exit `1` and name the budget; empty content exits `2` as a corrupt document.
