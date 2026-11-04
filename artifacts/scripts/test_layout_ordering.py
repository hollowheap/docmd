#!/usr/bin/env python3
"""Test layout ordering with rapid-layout."""

import io
from pathlib import Path
import pymupdf
from rapid_layout import RapidLayout
from rapidocr import RapidOCR

DATASET = Path("artifacts/scratch/INF2002")

def test_nyt_image():
    doc = pymupdf.open(DATASET / "6 - Visual Design.pdf")
    img_bytes = doc.extract_image(30)["image"]
    doc.close()

    ocr = RapidOCR()
    layout = RapidLayout()

    layout_res = layout(img_bytes)
    ocr_res = ocr(img_bytes)

    print("=== NYT Image (xref 30) Layout Blocks ===")
    for box, cls, score in zip(layout_res.boxes, layout_res.class_names, layout_res.scores):
        print(f"  {cls:12s} ({score:.2f}): {[round(v, 1) for v in box]}")

    raw_items = []
    if ocr_res and hasattr(ocr_res, "boxes") and ocr_res.boxes is not None:
        raw_items = list(zip(ocr_res.boxes, ocr_res.txts, ocr_res.scores))
    elif isinstance(ocr_res, tuple) and ocr_res[0]:
        raw_items = ocr_res[0]

    print(f"\nTotal OCR items: {len(raw_items)}")

if __name__ == "__main__":
    test_nyt_image()
