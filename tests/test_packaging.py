from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "docmd"


def script_metadata() -> dict:
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    start = lines.index("# /// script")
    end = lines.index("# ///", start + 1)
    block = "\n".join(
        line[2:] if line.startswith("# ") else line[1:] for line in lines[start + 1 : end]
    )
    return tomllib.loads(block)


def test_dependency_parity() -> None:
    metadata = script_metadata()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

    assert metadata["requires-python"] == pyproject["project"]["requires-python"]
    assert metadata["dependencies"] == pyproject["project"]["dependencies"]
    assert metadata["tool"]["uv"]["override-dependencies"] == (
        pyproject["tool"]["uv"]["override-dependencies"]
    )

    locked = {package["name"] for package in lock["package"]}
    for requirement in metadata["dependencies"]:
        name = re.match(r"[A-Za-z0-9_.-]+", requirement)
        assert name is not None
        assert name.group() in locked

    assert "opencv-python-headless" in locked
    assert "opencv-python" in locked
