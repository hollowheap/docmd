from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pymupdf
from docx import Document

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docmd"


def run_docmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def test_success_exit_zero(tmp_path: Path) -> None:
    document = Document()
    document.add_paragraph("Hello")
    source = tmp_path / "ok.docx"
    document.save(source)

    result = run_docmd(str(source), "--stdout")

    assert result.returncode == 0, result.stderr
    assert "Hello" in result.stdout


def test_cli_failure_exit_one(tmp_path: Path) -> None:
    missing = run_docmd(str(tmp_path / "missing.docx"))
    assert missing.returncode == 1

    usage = run_docmd()
    assert usage.returncode == 1
    assert "usage:" in usage.stderr.lower()

    unsupported = tmp_path / "note.txt"
    unsupported.write_text("hello")
    result = run_docmd(str(unsupported), "--stdout")
    assert result.returncode == 1


def test_corrupt_document_exit_two(tmp_path: Path) -> None:
    for suffix in (".docx", ".pptx", ".pdf"):
        source = tmp_path / f"bad{suffix}"
        source.write_bytes(b"not a valid document")
        result = run_docmd(str(source), "--stdout")
        assert result.returncode == 2, (suffix, result.stderr)
        assert result.stderr


def test_encrypted_pdf_exit_three(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Secret")
    source = tmp_path / "secret.pdf"
    document.save(
        source,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="secret",
    )
    document.close()

    missing_password = run_docmd(str(source), "--stdout")
    assert missing_password.returncode == 3

    wrong_password = run_docmd(str(source), "--stdout", "--password", "wrong")
    assert wrong_password.returncode == 3

    correct_password = run_docmd(str(source), "--stdout", "--password", "secret")
    assert correct_password.returncode == 0, correct_password.stderr
    assert "Secret" in correct_password.stdout


def test_usage_error_exit_one() -> None:
    unknown_option = run_docmd("--not-an-option")

    assert unknown_option.returncode == 1
    assert "usage:" in unknown_option.stderr.lower()
    assert "error" in unknown_option.stderr.lower()

    missing_value = run_docmd("input.docx", "-o")

    assert missing_value.returncode == 1
    assert "usage:" in missing_value.stderr.lower()


def test_unsupported_extension(tmp_path: Path) -> None:
    source = tmp_path / "note.txt"
    source.write_text("hello", encoding="utf-8")
    output = tmp_path / "out.md"

    result = run_docmd(str(source), "-o", str(output))

    assert result.returncode == 1
    assert "unsupported input format" in result.stderr
    assert not output.exists()

    upper = tmp_path / "NOTE.TXT"
    upper.write_text("hello", encoding="utf-8")
    upper_result = run_docmd(str(upper), "--stdout")

    assert upper_result.returncode == 1
    assert "unsupported input format" in upper_result.stderr
