# docmd

Convert DOCX, PPTX, and PDF documents into GitHub Flavored Markdown.

`docmd` is a single-file [PEP 723](https://peps.python.org/pep-0723/) CLI. Run it with [`uv`](https://docs.astral.sh/uv/) and it resolves its own dependencies on first use, with no pre-created virtual environment.

## Features

- DOCX headings, lists, tables, images, and inline text.
- PPTX slides, tables, speaker notes, and pictures.
- PDF layout inference: font-size headings, multi-column reading order, running header/footer removal, and image captions.
- Offline OCR for scanned pages and text inside embedded images.
- GitHub Flavored Markdown tables with merged-cell flattening and strict column alignment.
- File mode writes `<name>.md` plus a sibling `<name>.assets/` directory.
- `--stdout` keeps images inline as Base64 data URIs.
- `--verify` checks table columns, code fences, and local asset links.
- Deterministic directory conversion with `--jobs N`.

## Requirements

- Python 3.11 or newer.
- `uv` to run the script.
- Linux, macOS, or Windows. OCR runs on CPU by default; OpenVINO can use an Intel GPU or NPU when available.

## Quick start

```bash
# Print Markdown to stdout
uv run --script scripts/docmd document.pdf --stdout

# Write Markdown and extracted assets
uv run --script scripts/docmd document.pdf -o ./out --verify

# Convert a directory recursively
uv run --script scripts/docmd ./documents -o ./out --jobs 4
```

Run `uv run --script scripts/docmd --version` to check the installed version.

## CLI

```text
docmd INPUT [-o PATH] [--stdout] [--no-images] [--no-ocr]
      [--password SECRET] [--verify] [-j N] [-q] [-v] [-h]
```

| Option | Behavior |
| --- | --- |
| `-o, --out PATH` | Output file or directory. Default: `./out/`. A suffix writes that file; no suffix writes `<stem>.md` inside the directory. |
| `--stdout` | Write Markdown to stdout and inline images as data URIs. Directory input is rejected. |
| `--no-images` | Omit image extraction and image Markdown. |
| `--no-ocr` | Disable page OCR and image captions. |
| `--password SECRET` | Password for encrypted documents. |
| `--verify` | Validate generated Markdown before finishing. |
| `-j, --jobs N` | Concurrent documents for directory input. Default: `2`. |
| `-q, --quiet` | Suppress progress logs. |
| `-v, --version` | Print the version. |
| `-h, --help` | Print usage. |

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | CLI or runtime failure. |
| `2` | Corrupt document. |
| `3` | Encrypted document without a valid password. |

## OCR

OCR uses [RapidOCR](https://github.com/RapidAI/RapidOCR) models through OpenVINO. The default backend is CPU.

```bash
# Force a backend: cpu, gpu, npu, or auto
DOCMD_OCR_DEVICE=gpu uv run --script scripts/docmd scan.pdf --stdout

# Limit OpenVINO CPU inference threads
DOCMD_OCR_THREADS=4 uv run --script scripts/docmd scan.pdf --stdout
```

`DOCMD_OCR_DEVICE=auto` tries GPU, then NPU, then CPU. The default `cpu` is the fastest option on this machine for the bundled OCR models. OCR results for identical images are cached for the duration of a conversion.

PDF pages with fewer than 50 extractable characters trigger OCR fallback. Image text is emitted as `> *[Image Text]*: ...` beneath the image.

## Output

File mode:

```text
out/
├── document.md
└── document.assets/
    ├── image-001.png
    └── image-002.jpg
```

Images are referenced with relative links. `--stdout` keeps them inline as `data:` URIs. Non-image and non-base64 data URIs stay inline.

## Install as a skill

The publishable skill tree lives in `skills/docmd/`.

```bash
npx skills add <owner>/docmd --skill docmd
```

The skill directory contains `SKILL.md`, `README.md`, a script README, per-format reference guides, and sample fixtures.

## Development

```bash
# Full test suite
uv run pytest -q

# One check
uv run pytest tests/test_verify.py::test_asset_links -q

# Rebuild the packaged skill and smoke-convert fixtures
uv run python scripts/dist.py
```

`scripts/docmd` is the source of truth. `scripts/dist.py` syncs it into `skills/docmd/scripts/docmd`, validates the SKILL.md frontmatter and PEP 723 metadata, and smoke-converts each fixture.

Keep PEP 723 dependencies in `scripts/docmd` in sync with `pyproject.toml`, then run `uv lock`. Keep `opencv-python-headless` and the `opencv-python` override in both manifests; RapidOCR imports fail without this pairing.

## License

MIT. See [LICENSE](LICENSE).
