# Decisions

- [x] D01 [R01]: Ship `docmd` as a Python 3.11+ single-file PEP 723 CLI run with `uv`
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - zero-install execution mirrors md-questioner and avoids environment drift

- [x] D02 [R02]: Use `python-docx` for `.docx` parsing
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - native access to styles, tables, and embedded media

- [x] D03 [R02]: Use `python-pptx` for `.pptx` parsing
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - native access to slides, shapes, speaker notes, and media

- [x] D04 [R02]: Use `pymupdf` (`fitz`) for `.pdf` parsing
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - one dependency covers layout, text spans, fonts, and image streams

- [x] D05 [R04]: Use `rapidocr-onnxruntime` for OCR
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - bundled CPU ONNX models run offline without system binaries such as tesseract

- [x] D06 [R06]: CLI accepts an input path plus `-o/--out`, `--stdout`, `--no-images`, `--no-ocr`, `--password`, `--verify`, `-q/--quiet`, `-v/--version`, and `-h/--help`
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - stable interface for agents and scripts

- [x] D07 [R07]: Exit `0` on success, `1` on CLI/runtime failure, `2` on corrupt documents, and `3` on encrypted documents without a valid password
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - machine-actionable failure classes

- [x] D08 [R03]: File mode writes a sibling `<filename>.assets/` directory with relative links; `--stdout` inlines images as Base64 data URIs; `--no-images` omits image syntax
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - avoid orphan files in pipes while keeping file-mode asset links predictable

- [x] D09 [R04]: OCR runs on PDF pages with fewer than 50 extractable characters, transcribes embedded images into blockquote captions, and reconciles OCR against digital text
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - recover scanned and diagram text without duplicating searchable content

- [x] D10 [R02]: Apply format-specific layout rules for PPTX slide headings and notes, DOCX heading styles and font promotion, PDF font-cluster headings, multi-column order, running header/footer suppression, and GFM tables
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - preserve document hierarchy and reading order

- [x] D11 [R05]: Directory input recurses through non-hidden `.docx`, `.pptx`, and `.pdf` files and mirrors the input hierarchy in the output tree
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - predictable batch conversion

- [x] D12 [R08]: `--verify` checks GFM table column alignment, balanced code fences, and resolvable non-empty asset links
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - catch broken Markdown before downstream use

- [x] D13 [R09]: `skills/docmd/` contains `SKILL.md`, `scripts/docmd`, `scripts/README.md`, reference guides, and fixtures
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - md-questioner-compatible skill distribution

- [x] D14 [R09]: `scripts/dist.py` builds the distribution and runs smoke conversions on sample fixtures
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - verify the packaged artifact before distribution

## Non-Goals

- None recorded.

- [x] D15 [R09]: Publish the skill from this repository as a monorepo skill at `skills/docmd/`, installed with `npx skills add <owner>/<repo> --skill docmd`; `scripts/docmd` stays the source of truth and `scripts/dist.py` syncs it into the published tree
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - skills.sh indexes public GitHub repos with no upload step, and one authored tree avoids drift between copies

- [x] D16 [R09]: Ship the skill under MIT with `SKILL.md` frontmatter carrying `name`, `description`, `license`, `compatibility`, and `metadata.version`, and link the three reference guides from `SKILL.md`
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - agents may reproduce the skill verbatim, and linked guides are what make progressive disclosure work

- [x] D17 [R05]: Convert directory documents in isolated subprocess workers with `--jobs N`, defaulting to 2
  - Alternatives: Not recorded.
  - Consequences: Not recorded.
  - OCR is CPU-bound, each worker already uses multiple cores, and separate processes avoid sharing PyMuPDF and RapidOCR state
