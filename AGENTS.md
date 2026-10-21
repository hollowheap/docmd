# AGENTS.md

`docmd` converts DOCX/PPTX/PDF to GitHub Flavored Markdown. `scripts/docmd` is the source of truth; `skills/docmd/` is the publishable skill tree.

## Commands

- Full suite: `uv run pytest -q` (~60s; OCR tests dominate).
- Single check: `uv run pytest tests/test_verify.py::test_asset_links -q`.
- CLI: `uv run --script scripts/docmd --version`; convert with `uv run --script scripts/docmd <input> --stdout`.
- Exit codes: `0` success, `1` CLI/runtime failure, `2` corrupt document, `3` encrypted without a valid password.
- No lint, typecheck, or formatter config; pytest is the verification gate.
- Task workflow: `~/.config/opencode/skills/implement/scripts/artifacts.sh next-tasks`, then `context <TASK-id>`. Mark `artifacts/plan.md` only after its verify command passes.

## Packaging

- Edit `scripts/docmd`, not `skills/docmd/`. `skills/docmd/` is the publishable tree: `SKILL.md`, `README.md`, scripts README, reference guides, and fixtures.
- `scripts/dist.py` syncs `scripts/docmd` into `skills/docmd/scripts/docmd` (mode `0755`), validates the SKILL.md frontmatter and PEP 723 metadata, and smoke-converts every fixture. Run it after any change to `scripts/docmd`.
- `scripts/docmd` is a PEP 723 script. Keep its `dependencies` in sync with `pyproject.toml`; run `uv lock` after dependency changes.
- Keep `opencv-python-headless` and the `opencv-python` override in both manifests. RapidOCR imports fail without this pairing.

## Distribution

- skills.sh indexes public GitHub repos; there is no upload step. Publish by pushing this repository and installing with `npx skills add <owner>/<repo> --skill docmd`.
- The skill directory name must match the SKILL.md `name` field (`docmd`), and `SKILL.md` must stay at `skills/docmd/SKILL.md`.
- `SKILL.md` frontmatter must keep `name`, `description`, `license`, `compatibility`, and `metadata.version`; `scripts/dist.py` fails the build when any is missing.

## Conversion seams

- Converters emit images as `![](data:image/...;base64,...)`. `write_markdown` extracts them into sibling `<stem>.assets/` for file output; `--stdout` keeps data URIs. Follow this seam for new image sources.
- `--verify` checks fences, GFM table column counts, and local links, including missing or zero-byte assets. File mode verifies after writing assets, so links resolve against the output directory.
- PDF OCR fallback triggers at fewer than 50 extractable characters. Test PDFs with short digital text will OCR unexpectedly; pass `--no-ocr` or use more than 50 characters.
- Directory input mirrors subfolders under `-o`, skips dot-prefixed paths, writes sibling assets, and rejects `--stdout`.
- In file mode, `-o` is classified by `Path.suffix`; a path containing a dot is treated as a file. Use a non-dotted output directory or an explicit `.md` path. Directory input always treats `-o` as the output root.

## Tests and fixtures

- Tests use subprocess CLI calls; `tests/test_verify.py` also imports `scripts/docmd` as a module.
- OCR tests are offline but slow; use `--no-ocr` for tests that do not exercise OCR.
- `skills/docmd/references/fixtures/sample.{docx,pptx,pdf}` share the stem `sample`; convert them into separate output roots or `sample.md` is overwritten.

## References

- `artifacts/specs.md` and `artifacts/decisions.md`: settled contracts.
- `artifacts/plan.md`: active task queue and per-task verify commands.
- `artifacts/context.md`: early scaffold notes; it predates the implementation and is stale on test status.
