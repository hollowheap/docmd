#!/usr/bin/env python3
"""Report structural metrics for a local docmd bench corpus.

Set DOCMD_BENCH_DIR to a directory of DOCX, PPTX, or PDF files. The corpus is
never committed; the INF2002 lecture deck used during the review lives outside
the repository.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "docmd"
DEFAULT_BENCH_DIR = ROOT / "artifacts" / "scratch" / "INF2002"


def load_docmd():
    loader = SourceFileLoader("docmd_bench", str(SCRIPT))
    return loader.load_module()


def metrics(markdown: str) -> dict[str, int]:
    visible = re.sub(r"data:[^)]+", "data:", markdown)
    lines = visible.splitlines()
    words = re.findall(r"\b[\w'-]+\b", visible)
    return {
        "words": len(words),
        "unique_words": len({word.casefold() for word in words}),
        "heading_lines": sum(1 for line in lines if re.match(r"^#{1,6}\s", line)),
        "table_rows": sum(1 for line in lines if line.strip().startswith("|")),
        "links": len(re.findall(r"(?<!!)\[[^\]]*\]\([^)]+\)", visible)),
        "images": len(re.findall(r"!\[[^\]]*\]\([^)]+\)", visible)),
        "ocr_blocks": visible.count("> *[Image Text]*:"),
        "characters": len(visible),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Convert at most this many documents (0 means all).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Also write the Markdown table to this path.",
    )
    args = parser.parse_args()

    bench_dir = Path(
        os.environ.get("DOCMD_BENCH_DIR", str(DEFAULT_BENCH_DIR))
    ).resolve()
    if not bench_dir.is_dir():
        print(
            f"docmd bench: set DOCMD_BENCH_DIR to a directory of documents; "
            f"{bench_dir} is not a directory",
            file=sys.stderr,
        )
        return 1

    docmd = load_docmd()
    documents = docmd.discover_documents(bench_dir)
    if args.limit:
        documents = documents[: args.limit]
    if not documents:
        print(f"docmd bench: no documents in {bench_dir}", file=sys.stderr)
        return 1

    options = docmd.ConversionOptions(use_ocr=not args.no_ocr, quiet=True)
    rows = []
    for document in documents:
        started = time.perf_counter()
        markdown, status = docmd.convert_source(document, options)
        elapsed = time.perf_counter() - started
        if status != 0 or markdown is None:
            print(
                f"{document.relative_to(bench_dir)}: exit {status}",
                file=sys.stderr,
            )
            continue
        values = metrics(markdown)
        values["seconds"] = round(elapsed, 2)
        rows.append((document.relative_to(bench_dir).as_posix(), values))

    if not rows:
        return 1

    columns = [
        "document",
        "words",
        "unique_words",
        "heading_lines",
        "table_rows",
        "links",
        "images",
        "ocr_blocks",
        "characters",
        "seconds",
    ]
    output_lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for name, values in rows:
        output_lines.append(
            "| "
            + " | ".join(
                [name]
                + [str(values[column]) for column in columns[1:]]
            )
            + " |"
        )
    rendered = "\n".join(output_lines) + "\n"
    print(rendered, end="")
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
