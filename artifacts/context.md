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
- `write_markdown` extracts data-URI images into sibling `<stem>.assets/`; `--stdout` keeps data URIs.
- `verify_markdown` checks balanced fences, GFM table column counts, and local asset existence/size.
- Directory input: `discover_documents` skips dot-prefixed paths; `convert_directory` uses warm in-process workers (`--jobs N`, default 2) with shared OCR engine and cache.
- PDF: span extraction, margin stripping, `rapid-layout` PP-Structure column ordering, heading clusters, OCR fallback below 50 chars, captions, and deduplication.
- PPTX: slide headings, body text, tables, pictures, and speaker notes. DOCX: headings, lists, tables, and images.
- Dist reference: `skills/docmd/references/{docx,pptx,pdf}.md` plus `skills/docmd/references/fixtures/sample.{docx,pptx,pdf}`.
- Builder: `scripts/dist.py` syncs `scripts/docmd` into `skills/docmd/scripts/docmd`, validates SKILL.md frontmatter and PEP 723 metadata, then smoke-converts each fixture.

## Gotchas

- Keep PEP 723 `dependencies` in `scripts/docmd` in sync with `pyproject.toml`.
- Keep `opencv-python-headless` in both manifests; RapidOCR imports fail without it.
- PDFs with fewer than 50 extractable characters trigger OCR; pass `--no-ocr` or use longer digital text for layout tests.
- `-o` is classified by `Path.suffix`; a directory path containing a dot is treated as a file.
- `skills/docmd/references/fixtures/sample.*` share the stem `sample`; use separate output roots to avoid overwriting `sample.md`.

## Distribution

- skills.sh indexes public GitHub repos; there is no upload step.
- Install: `npx skills add <owner>/<repo> --skill docmd`; the skill lives at `skills/docmd/SKILL.md`.
- SKILL.md frontmatter must keep `name`, `description`, `license`, `compatibility`, and `metadata.version`; the directory name must equal `name`.
