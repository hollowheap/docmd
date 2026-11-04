#!/usr/bin/env python3
"""Benchmark INF2002 dataset conversions with docmd."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "docmd"
DATASET = ROOT / "artifacts" / "scratch" / "INF2002"


def load_docmd():
    loader = SourceFileLoader("docmd", str(SCRIPT))
    return loader.load_module()


def run_cli(args: list[str]) -> tuple[float, int, str, str]:
    t0 = time.perf_counter()
    res = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    duration = time.perf_counter() - t0
    return duration, res.returncode, res.stdout, res.stderr


def benchmark_dataset(skip_no_ocr: bool = False, skip_batch: bool = False, jobs_list: list[int] | None = None):
    docmd = load_docmd()
    docs = docmd.discover_documents(DATASET)
    print(f"Discovered {len(docs)} documents in {DATASET}:", flush=True)
    for d in docs:
        print(f"  - {d.name} ({d.stat().st_size:,} bytes)", flush=True)

    results = {}

    # 1. No OCR Batch
    if not skip_no_ocr:
        print("\n--- Benchmarking Directory Conversion (No OCR) ---", flush=True)
        jobs_to_test = jobs_list or [1, 2, 4]
        for jobs in jobs_to_test:
            runs = []
            for r in range(2):
                with tempfile.TemporaryDirectory(prefix=f"bench-inf2002-no-ocr-{jobs}-") as tmp:
                    dur, code, stdout, stderr = run_cli([
                        str(DATASET),
                        "-o",
                        str(tmp),
                        "--no-ocr",
                        "--jobs",
                        str(jobs),
                    ])
                    if code != 0:
                        print(f"Failed jobs={jobs}: {stderr}", file=sys.stderr, flush=True)
                    runs.append(dur)
            results[f"no_ocr_jobs_{jobs}"] = {
                "mean": statistics.mean(runs),
                "min": min(runs),
                "runs": runs,
            }
            print(f"  No OCR (jobs={jobs}): min={min(runs):.3f}s, mean={statistics.mean(runs):.3f}s", flush=True)

    # 2. Warm In-Process Single Document Timings (Per File Profiling)
    print("\n--- Profiling Documents with Warm Engine (In-Process) ---", flush=True)
    engine = docmd.load_ocr_engine()
    cache = docmd.OcrCache()
    opts_ocr = docmd.ConversionOptions(use_ocr=True)
    opts_no_ocr = docmd.ConversionOptions(use_ocr=False)

    doc_profiles = []
    warmup_doc = DATASET / "L1 - Design Sprint.pdf"
    docmd.convert_source(warmup_doc, opts_ocr, ocr_engine=engine, ocr_cache=cache)

    for d in docs:
        t0 = time.perf_counter()
        md_no_ocr, code_no = docmd.convert_source(d, opts_no_ocr)
        t_no_ocr = time.perf_counter() - t0

        cache_before = len(cache)
        t0 = time.perf_counter()
        md_ocr, code_ocr = docmd.convert_source(d, opts_ocr, ocr_engine=engine, ocr_cache=cache)
        t_ocr = time.perf_counter() - t0
        new_cached = len(cache) - cache_before

        doc_profiles.append({
            "name": d.name,
            "size_kb": round(d.stat().st_size / 1024, 1),
            "no_ocr_s": round(t_no_ocr, 3),
            "warm_ocr_s": round(t_ocr, 3),
            "new_images_cached": new_cached,
            "total_cached": len(cache),
            "md_kb": round(len(md_ocr.encode("utf-8")) / 1024, 1) if md_ocr else 0,
        })
        print(
            f"  {d.name:<45} | No OCR: {t_no_ocr:6.3f}s | Warm OCR: {t_ocr:6.3f}s | +{new_cached:2d} imgs (total {len(cache):3d})",
            flush=True,
        )

    results["doc_profiles"] = doc_profiles

    # 3. Full Batch with OCR and Warm Engine
    if not skip_batch:
        print("\n--- Benchmarking Directory Conversion (With OCR, Warm Engine) ---", flush=True)
        jobs_to_test = jobs_list or [4]
        for jobs in jobs_to_test:
            with tempfile.TemporaryDirectory(prefix=f"bench-inf2002-ocr-{jobs}-") as tmp:
                dur, code, stdout, stderr = run_cli([
                    str(DATASET),
                    "-o",
                    str(tmp),
                    "--jobs",
                    str(jobs),
                ])
                if code != 0:
                    print(f"Failed OCR jobs={jobs}: {stderr}", file=sys.stderr, flush=True)
                results[f"ocr_jobs_{jobs}"] = dur
                print(f"  With OCR (jobs={jobs}): {dur:.2f}s", flush=True)

    print("\n--- Benchmark Complete ---", flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark INF2002 dataset conversions.")
    parser.add_argument("--skip-no-ocr", action="store_true", help="Skip No-OCR batch.")
    parser.add_argument("--skip-batch", action="store_true", help="Skip full batch OCR.")
    parser.add_argument("-j", "--jobs", type=int, default=None, help="Specific jobs count.")
    args = parser.parse_args()

    jobs_list = [args.jobs] if args.jobs else None
    benchmark_dataset(skip_no_ocr=args.skip_no_ocr, skip_batch=args.skip_batch, jobs_list=jobs_list)
