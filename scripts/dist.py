#!/usr/bin/env python3
"""Sync the publishable docmd skill tree and smoke-test its conversions."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "docmd"
SKILL_ROOT = ROOT / "skills" / "docmd"
PACKAGED = SKILL_ROOT / "scripts" / "docmd"
FIXTURES = SKILL_ROOT / "references" / "fixtures"
FIXTURE_NAMES = ("sample.docx", "sample.pptx", "sample.pdf")
STATIC_FILES = (
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "README.md",
    SKILL_ROOT / "scripts" / "README.md",
    SKILL_ROOT / "references" / "docx.md",
    SKILL_ROOT / "references" / "pptx.md",
    SKILL_ROOT / "references" / "pdf.md",
    *(FIXTURES / name for name in FIXTURE_NAMES),
)
PEP723_SHEBANG = "#!/usr/bin/env -S uv run --script"
PEP723_MARKERS = (
    "# /// script",
    'requires-python = ">=3.11"',
    "dependencies = [",
    "# ///",
)
REQUIRED_FRONTMATTER = ("name", "description", "license", "compatibility")


def frontmatter_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not text.startswith("---\n"):
        return fields
    block = text.split("\n---", 1)[0].removeprefix("---\n")
    parent = ""
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = line.partition(":")
        if line[:1].isspace():
            if parent:
                fields[f"{parent}.{key.strip()}"] = value.strip().strip('"')
            continue
        parent = key.strip()
        fields[parent] = value.strip()
    return fields


def build() -> None:
    missing = [str(path.relative_to(ROOT)) for path in STATIC_FILES if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing skill sources: {', '.join(missing)}")

    source = SOURCE.read_text(encoding="utf-8")
    missing_metadata = [marker for marker in PEP723_MARKERS if marker not in source]
    if not source.startswith(PEP723_SHEBANG) or missing_metadata:
        raise SystemExit(f"{SOURCE.relative_to(ROOT)} is missing PEP 723 metadata")

    fields = frontmatter_fields((SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"))
    missing_fields = [key for key in REQUIRED_FRONTMATTER if not fields.get(key)]
    if missing_fields:
        raise SystemExit(f"SKILL.md is missing frontmatter: {', '.join(missing_fields)}")
    if fields["name"] != SKILL_ROOT.name:
        raise SystemExit(
            f"SKILL.md name {fields['name']!r} does not match {SKILL_ROOT.name!r}"
        )

    PACKAGED.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, PACKAGED)
    PACKAGED.chmod(0o755)
    print(f"Packaged {PACKAGED.relative_to(ROOT)}")


def smoke() -> None:
    if not PACKAGED.is_file():
        raise SystemExit("Packaged script missing; run build first")

    for name in FIXTURE_NAMES:
        fixture = FIXTURES / name
        with tempfile.TemporaryDirectory(prefix=f"docmd-{fixture.stem}-") as tmp:
            output = Path(tmp) / f"{fixture.stem}-{fixture.suffix.lstrip('.')}.md"
            assets = output.parent / f"{output.stem}.assets"
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "--script",
                    str(PACKAGED),
                    str(fixture),
                    "-o",
                    str(output),
                    "--no-ocr",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise SystemExit(f"Conversion failed for {name}:\n{result.stderr}")
            if not output.is_file() or not output.read_text(encoding="utf-8").strip():
                raise SystemExit(f"Empty Markdown for {name}")
            if not assets.is_dir() or not any(path.is_file() for path in assets.iterdir()):
                raise SystemExit(f"Missing extracted assets for {name}")
            print(f"Smoke-converted {name}")


def main() -> int:
    build()
    smoke()
    return 0


if __name__ == "__main__":
    sys.exit(main())
