# Context

## Stack & Entrypoints

- Python 3.12 pinned via `.python-version`; `pyproject.toml` requires `>=3.11`.
- Source of truth: `scripts/docmd`, a single-file PEP 723 CLI.
- Packaged skill tree: `skills/docmd/SKILL.md`, `skills/docmd/README.md`, `skills/docmd/scripts/README.md`, `skills/docmd/references/` guides and fixtures.
- Tests invoke the CLI as a subprocess; `tests/test_verify.py` also loads it as a module.
- No lint, typecheck, or formatter config; pytest is the verification gate.

## Architecture

- Architecture specification: [architecture.md](architecture.md).
- Architectural exploration: [brainstorm.md](brainstorm.md).
- Design questions: [questions.md](questions.md).

## Module Seams

- `main` -> `convert_source` -> `convert_document` -> `convert_docx` / `convert_pptx` / `convert_pdf`.
- `write_markdown` extracts data-URI images into sibling `<stem>.assets/`, replacing generated `image-NNN` files while keeping unrelated files; `--stdout` keeps data URIs.
- `verify_markdown` checks balanced fences, single- and multi-column tables (including quoted tables), inline/reference/HTML asset links, and local asset existence/size; `verify_markdown_counts` reports coverage.
- Directory input: `discover_documents` skips dot-prefixed paths; `convert_directory` stages in-process workers (`--jobs N`, default 2), then commits in sorted document order and stops at the first failure. Workers share the OCR engine and cache.
- PDF: span extraction, digital/OCR merge, margin stripping, `rapid-layout` block ordering with logged geometric fallback, heading clusters, paragraph gaps, lists, aligned text tables, dehyphenation, link annotations, image captions, and duplicate suppression. OCR triggers below 50 digital characters or a dominant image over 60 percent of the page.
- PPTX: visual-order shapes, bullet text, tables, charts, SmartArt text, pictures, omission comments, and speaker notes. DOCX: headings, run formatting, hyperlinks, numbering, merged tables, and images (including table cells).
- Dist reference: `skills/docmd/references/{docx,pptx,pdf}.md` plus `skills/docmd/references/fixtures/sample.{docx,pptx,pdf}`.
- Builder: `scripts/dist.py` syncs `scripts/docmd` into `skills/docmd/scripts/docmd`, validates SKILL.md frontmatter and PEP 723 metadata, then smoke-converts each fixture.

## Gotchas

- Keep PEP 723 `dependencies` in `scripts/docmd` in sync with `pyproject.toml`.
- Keep `opencv-python-headless` in both manifests; RapidOCR imports fail without it.
- PDFs with fewer than 50 extractable characters (or a dominant full-page image) trigger OCR; OCR fills gaps but never replaces digital lines. Pass `--no-ocr` or use longer digital text for layout tests.
- OCR environment values are validated before conversion; invalid `DOCMD_OCR_DEVICE`, `DOCMD_OCR_MODEL`, or `DOCMD_OCR_CONFIDENCE` exits 1.
- Resource budgets use `DOCMD_MAX_BYTES`, `DOCMD_MAX_PAGES`, and `DOCMD_MAX_IMAGE_PIXELS`; exceeding one exits 1.
- Typography normalisation is prose-only and can be disabled with `--no-sanitize`.
- `-o` is classified by `Path.suffix`; a directory path containing a dot is treated as a file.
- `skills/docmd/references/fixtures/sample.*` share the stem `sample`; use separate output roots to avoid overwriting `sample.md`.

## Distribution

- skills.sh indexes public GitHub repos; there is no upload step.
- Install: `npx skills add <owner>/<repo> --skill docmd`; the skill lives at `skills/docmd/SKILL.md`.
- SKILL.md frontmatter must keep `name`, `description`, `license`, `compatibility`, and `metadata.version`; the directory name must equal `name`.
