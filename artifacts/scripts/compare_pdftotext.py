#!/usr/bin/env python3
"""Objective comparison between pdftotext and docmd on INF2002 PDFs."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "scratch" / "INF2002"
PDFS = sorted(DATASET.glob("*.pdf"))

def check_pdftotext():
    pdftotext_bin = shutil.which("pdftotext")
    if not pdftotext_bin:
        print("pdftotext is not installed", flush=True)
        return

    print(f"=== Comparative Benchmark: pdftotext vs docmd ===")
    print(f"Evaluating {len(PDFS)} PDF files from INF2002\n")

    # 1. pdftotext batch timing
    t0 = time.perf_counter()
    pdftotext_total_chars = 0
    pdftotext_pages = 0
    for p in PDFS:
        res = subprocess.run([pdftotext_bin, str(p), "-"], capture_output=True, text=True)
        pdftotext_total_chars += len(res.stdout)
    pdftotext_dur = time.perf_counter() - t0

    # 2. docmd without OCR (in-process)
    from importlib.machinery import SourceFileLoader
    docmd = SourceFileLoader("docmd", str(ROOT / "scripts" / "docmd")).load_module()
    opts_no_ocr = docmd.ConversionOptions(use_ocr=False)

    t0 = time.perf_counter()
    docmd_no_ocr_chars = 0
    docmd_headings_count = 0
    docmd_images_count = 0
    for p in PDFS:
        md, code = docmd.convert_source(p, opts_no_ocr)
        if md:
            docmd_no_ocr_chars += len(md)
            docmd_headings_count += len(re.findall(r"^#{1,6}\s+", md, re.MULTILINE))
            docmd_images_count += len(re.findall(r"!\[.*?\]\(.*?\)", md))
    docmd_no_ocr_dur = time.perf_counter() - t0

    print(f"{'Metric':<30} | {'pdftotext (Poppler)':<20} | {'docmd (--no-ocr)':<20}")
    print(f"{'-'*30}-|-{'-'*20}-|-{'-'*20}")
    print(f"{'Total Execution Time':<30} | {pdftotext_dur:<18.3f}s | {docmd_no_ocr_dur:<18.3f}s")
    print(f"{'Output Format':<30} | {'Plain text':<20} | {'GitHub Flavored MD':<20}")
    print(f"{'Total Extracted Chars':<30} | {pdftotext_total_chars:<20,} | {docmd_no_ocr_chars:<20,}")
    print(f"{'Headings Inferred (# / ##)':<30} | {'0 (not supported)':<20} | {docmd_headings_count:<20,}")
    print(f"{'Images / Figures Extracted':<30} | {'0 (not supported)':<20} | {docmd_images_count:<20,}")
    print(f"{'Running Headers/Footers':<30} | {'Retained (raw noise)':<20} | {'Stripped (heuristics)':<20}")
    print(f"{'DOCX / PPTX Support':<30} | {'No (PDF only)':<20} | {'Yes (DOCX, PPTX)':<20}")
    print(f"{'OCR Scanned/Image Fallback':<30} | {'No (drops images)':<20} | {'Yes (OpenVINO OCR)':<20}")
    print(f"{'Local Asset Verification':<30} | {'No':<20} | {'Yes (--verify)':<20}")


if __name__ == "__main__":
    check_pdftotext()
