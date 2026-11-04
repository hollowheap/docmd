#!/usr/bin/env python3
"""Benchmark test samples for docmd conversion with and without OCR."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "docmd"
FIXTURES = ROOT / "skills" / "docmd" / "references" / "fixtures"


def load_docmd():
    loader = SourceFileLoader("docmd", str(SCRIPT))
    return loader.load_module()


def run_cli(args: list[str], env: dict[str, str] | None = None) -> tuple[float, int, str]:
    t0 = time.perf_counter()
    res = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    duration = time.perf_counter() - t0
    return duration, res.returncode, res.stderr


def run_benchmark(iterations: int = 3):
    docmd = load_docmd()
    results = []

    # 1. Per-sample benchmark
    samples = [
        ("sample.docx", False, ["--no-ocr"], "No OCR"),
        ("sample.pptx", False, ["--no-ocr"], "No OCR"),
        ("sample.pdf", False, ["--no-ocr"], "No OCR"),
        ("sample.pdf", True, [], "OCR (CPU, Cold)"),
    ]

    for filename, use_ocr, extra_flags, mode_name in samples:
        fixture_path = FIXTURES / filename
        label = f"{filename} ({mode_name})"

        # In-process timing
        in_process_times = []
        for _ in range(iterations):
            opts = docmd.ConversionOptions(use_ocr=use_ocr)
            t0 = time.perf_counter()
            markdown, code = docmd.convert_source(fixture_path, opts)
            in_process_times.append(time.perf_counter() - t0)

        # CLI timing + assets
        cli_times = []
        asset_count = 0
        asset_size = 0
        md_size = 0
        for _ in range(iterations):
            with tempfile.TemporaryDirectory(prefix=f"bench-{fixture_path.stem}-") as tmp:
                out_path = Path(tmp) / f"{fixture_path.stem}.md"
                args = [str(fixture_path), "-o", str(out_path), *extra_flags]
                duration, code, stderr = run_cli(args)
                if code != 0:
                    print(f"CLI failed for {label}: {stderr}", file=sys.stderr)
                cli_times.append(duration)
                if out_path.is_file():
                    md_size = out_path.stat().st_size
                assets_dir = Path(tmp) / f"{fixture_path.stem}.assets"
                if assets_dir.is_dir():
                    assets = list(assets_dir.iterdir())
                    asset_count = len(assets)
                    asset_size = sum(f.stat().st_size for f in assets if f.is_file())

        results.append({
            "sample": filename,
            "mode": mode_name,
            "in_process_mean": statistics.mean(in_process_times),
            "in_process_min": min(in_process_times),
            "cli_mean": statistics.mean(cli_times),
            "cli_min": min(cli_times),
            "md_bytes": md_size,
            "assets": asset_count,
            "asset_bytes": asset_size,
        })

    # Warm OCR in-process benchmark for sample.pdf
    pdf_fixture = FIXTURES / "sample.pdf"
    engine = docmd.load_ocr_engine()
    opts_ocr = docmd.ConversionOptions(use_ocr=True)
    # Warm up engine
    docmd.convert_source(pdf_fixture, opts_ocr, ocr_engine=engine)
    warm_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        docmd.convert_source(pdf_fixture, opts_ocr, ocr_engine=engine)
        warm_times.append(time.perf_counter() - t0)

    results.append({
        "sample": "sample.pdf",
        "mode": "OCR (CPU, Warm Engine)",
        "in_process_mean": statistics.mean(warm_times),
        "in_process_min": min(warm_times),
        "cli_mean": None,
        "cli_min": None,
        "md_bytes": md_size,
        "assets": asset_count,
        "asset_bytes": asset_size,
    })

    # 2. Batch directory conversion (No OCR vs With OCR)
    with tempfile.TemporaryDirectory(prefix="bench-batch-src-") as src_tmp:
        src_dir = Path(src_tmp)
        shutil.copyfile(FIXTURES / "sample.docx", src_dir / "doc.docx")
        shutil.copyfile(FIXTURES / "sample.pptx", src_dir / "slides.pptx")
        shutil.copyfile(FIXTURES / "sample.pdf", src_dir / "paper.pdf")

        for ocr_mode, flags, label in [
            (False, ["--no-ocr"], "No OCR"),
            (True, [], "With OCR"),
        ]:
            for jobs in (1, 2):
                batch_times = []
                for _ in range(iterations):
                    with tempfile.TemporaryDirectory(prefix=f"bench-batch-out-{jobs}-") as out_tmp:
                        duration, code, stderr = run_cli([
                            str(src_dir),
                            "-o",
                            str(out_tmp),
                            *flags,
                            "--jobs",
                            str(jobs),
                        ])
                        if code != 0:
                            print(f"Batch ({label}, {jobs} jobs) failed: {stderr}", file=sys.stderr)
                        batch_times.append(duration)

                results.append({
                    "sample": "Batch (3 files)",
                    "mode": f"Directory ({label}, --jobs {jobs})",
                    "in_process_mean": None,
                    "in_process_min": None,
                    "cli_mean": statistics.mean(batch_times),
                    "cli_min": min(batch_times),
                    "md_bytes": None,
                    "assets": None,
                    "asset_bytes": None,
                })

    # 3. OCR Thread Scaling for sample.pdf
    for threads in (1, 2, 4, 8):
        thread_env = os.environ.copy()
        thread_env["DOCMD_OCR_THREADS"] = str(threads)
        thread_times = []
        for _ in range(iterations):
            with tempfile.TemporaryDirectory(prefix=f"bench-thread-{threads}-") as tmp:
                out_path = Path(tmp) / "sample.md"
                duration, code, stderr = run_cli(
                    [str(pdf_fixture), "-o", str(out_path)],
                    env=thread_env,
                )
                if code != 0:
                    print(f"Thread scaling ({threads} threads) failed: {stderr}", file=sys.stderr)
                thread_times.append(duration)

        results.append({
            "sample": "sample.pdf (OCR Threads)",
            "mode": f"{threads} threads",
            "in_process_mean": None,
            "in_process_min": None,
            "cli_mean": statistics.mean(thread_times),
            "cli_min": min(thread_times),
            "md_bytes": None,
            "assets": None,
            "asset_bytes": None,
        })

    return results


def print_markdown_table(results: list[dict]):
    print("\n### Benchmark Results: Test Samples with OCR\n")
    print("| Workload | Configuration | In-Process Mean | In-Process Min | CLI E2E Mean | CLI E2E Min | Markdown Size | Assets |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in results:
        in_proc_mean = f"{r['in_process_mean'] * 1000:.1f} ms" if r['in_process_mean'] is not None else "-"
        in_proc_min = f"{r['in_process_min'] * 1000:.1f} ms" if r['in_process_min'] is not None else "-"
        cli_mean = f"{r['cli_mean']:.3f} s" if r['cli_mean'] is not None else "-"
        cli_min = f"{r['cli_min']:.3f} s" if r['cli_min'] is not None else "-"
        md_size = f"{r['md_bytes'] / 1024:.1f} KB" if r['md_bytes'] is not None else "-"
        assets_str = f"{r['assets']} files ({r['asset_bytes'] / 1024:.1f} KB)" if r['assets'] is not None else "-"
        print(f"| `{r['sample']}` | {r['mode']} | {in_proc_mean} | {in_proc_min} | {cli_mean} | {cli_min} | {md_size} | {assets_str} |")


def main():
    parser = argparse.ArgumentParser(description="Benchmark docmd test samples with OCR.")
    parser.add_argument("-n", "--iterations", type=int, default=3, help="Number of benchmark iterations (default: 3).")
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")
    args = parser.parse_args()

    results = run_benchmark(iterations=args.iterations)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_markdown_table(results)


if __name__ == "__main__":
    main()
