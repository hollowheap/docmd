from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def pin_ocr_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin OCR to one backend so policy tests do not depend on the host."""
    monkeypatch.setenv("DOCMD_OCR_DEVICE", "cpu")
    monkeypatch.setenv("DOCMD_OCR_MODEL", "tiny")
    monkeypatch.setenv("DOCMD_OCR_CONFIDENCE", "0.5")
