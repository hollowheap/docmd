from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "dist.py"
SKILL_ROOT = ROOT / "skills" / "docmd"
IGNORED = (".venv/", ".pytest_cache/", ".git/")


def load_builder() -> ModuleType:
    loader = SourceFileLoader("dist_builder", str(BUILDER))
    spec = spec_from_file_location("dist_builder", BUILDER, loader=loader)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(IGNORED) or "__pycache__" in relative:
            continue
        state[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return state


def run_builder() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/dist.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_clean_rebuild() -> None:
    packaged = SKILL_ROOT / "scripts" / "docmd"
    packaged.unlink(missing_ok=True)

    result = run_builder()

    assert result.returncode == 0, result.stderr
    assert packaged.is_file()
    assert os.access(packaged, os.X_OK)
    assert packaged.read_text(encoding="utf-8") == (
        ROOT / "scripts" / "docmd"
    ).read_text(encoding="utf-8")


def test_missing_source(tmp_path: Path, monkeypatch) -> None:
    builder = load_builder()
    source = tmp_path / "docmd"
    source.write_text(
        "#!/usr/bin/env -S uv run --script\n# /// script\n# ///\n",
        encoding="utf-8",
    )
    packaged = tmp_path / "skills" / "docmd" / "scripts" / "docmd"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("original", encoding="utf-8")

    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "SOURCE", source)
    monkeypatch.setattr(builder, "PACKAGED", packaged)

    monkeypatch.setattr(builder, "STATIC_FILES", (tmp_path / "missing.md",))
    with pytest.raises(SystemExit) as missing:
        builder.build()
    assert "Missing skill sources" in str(missing.value)
    assert packaged.read_text(encoding="utf-8") == "original"

    monkeypatch.setattr(builder, "STATIC_FILES", (source,))
    with pytest.raises(SystemExit) as metadata:
        builder.build()
    assert "PEP 723" in str(metadata.value)
    assert packaged.read_text(encoding="utf-8") == "original"


def test_idempotent() -> None:
    before = snapshot(ROOT)

    first = run_builder()
    assert first.returncode == 0, first.stderr
    after_first = snapshot(ROOT)
    skill_first = snapshot(SKILL_ROOT)

    second = run_builder()
    assert second.returncode == 0, second.stderr
    after_second = snapshot(ROOT)
    skill_second = snapshot(SKILL_ROOT)

    assert after_first == after_second
    assert skill_first == skill_second
    assert before == after_second

    packaged = SKILL_ROOT / "scripts" / "docmd"
    assert packaged.read_bytes() == (ROOT / "scripts" / "docmd").read_bytes()
    assert packaged.stat().st_mode & 0o777 == 0o755
