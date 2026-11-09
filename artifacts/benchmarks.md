# Benchmarks

Host measurements for `docmd` OCR and PDF conversion. Wall-clock numbers vary with thermal state, background load, and browser memory pressure; treat small differences as noise.

## Host

| Component | Value |
| --- | --- |
| CPU | Intel Core Ultra 7 155H |
| Cores / threads | 16 cores / 22 threads |
| CPU clock, rated | 400 MHz min, 4800 MHz max |
| CPU clock, observed during OCR | 1390 MHz average, 2500 MHz max |
| Memory | 15 GiB total, 23 GiB swap |
| iGPU | Intel Arc Graphics (Meteor Lake-P, PCI `8086:7d55`) |
| NPU | Intel AI Boost (PCI `8086:7d1d`, driver `intel_vpu`) |
| OS | NixOS 26.05 |
| Python | 3.12 |
| OCR stack | rapidocr 3.10.0, OpenVINO 2026.4.1, PP-OCRv6 |

Observed clocks were sampled from `/proc/cpuinfo` every 0.5 s during conversion. Rated clocks come from `lscpu` and `cpufreq`.

## Workload

`~/Drive/gdrive/SIT/INF2003/1 - DB and Relational Model.pdf`

| Property | Value |
| --- | --- |
| Pages | 35 |
| File size | 1.7 MB |
| Extractable text | 13,462 characters |
| Image references | 57 |
| Unique image payloads | 22 |
| Repeated image references | 35 |

The document is mostly digital text, so page-level OCR fallback does not dominate. Image OCR and repeated logo images do.

## Results

| Run | Wall time | Notes |
| --- | ---: | --- |
| No OCR (`--no-ocr`), low load | 4.5 s | Initial measurement, minimal background load |
| No OCR (`--no-ocr`), loaded host | 19.6 s | Same host under browser and memory pressure |
| OCR, rapidocr-onnxruntime, no cache | 116.2 s | Historical backend before migration |
| OCR, rapidocr-onnxruntime, image cache | 47.6 s | Cache keyed by image SHA-256 |
| OCR, PP-OCRv4 CPU, best observed | 17.6 s | Previous backend |
| OCR, PP-OCRv4 CPU, loaded host | 53.2 s | Same command under load |
| OCR, PP-OCRv4 GPU | 28.4 s | GPU compile and inference |
| OCR, PP-OCRv6 tiny CPU | 20.2 s | Default model, CPU fallback |
| OCR, PP-OCRv6 small CPU | 25.3 s | Larger model; slower and shorter logo captions |
| OCR, PP-OCRv6 tiny GPU | 13.8 s | Fastest observed with PP-OCRv6 |
| OCR, PP-OCRv6 NPU | not run | NPU compile still fails on driver 1.28.0 |

## PP-OCRv6 comparison

Same PDF and image-cache path:

| Engine | Wall time | Captions |
| --- | ---: | ---: |
| PP-OCRv4 CPU | 17.6 s | 42 |
| PP-OCRv6 tiny CPU | 20.2 s | 42 |
| PP-OCRv6 small CPU | 25.3 s | 32 |
| PP-OCRv6 tiny GPU | 13.8 s | 42 |

PP-OCRv6 tiny keeps the same caption count and runs fastest on GPU. PP-OCRv6 small is slower and truncates some logo captions on this document.

## Parity: PP-OCRv4 vs PP-OCRv6 tiny (INF2002)

Benchmark set: 18 PDFs from `~/Drive/gdrive/SIT/INF2002`, 28 MB, 18 Markdown outputs. Same file-mode extraction, image links, and cache. Text compared after NFKC and control-character cleanup, excluding `> *[Image Text]*` caption lines.

| Metric | Result |
| --- | ---: |
| Mean body sequence parity | 92.2% |
| Mean body word Jaccard | 85.8% |
| Caption count, v4 / v6 tiny | 237 / 241 |
| Exact caption matches | 3 / 237 |
| Image link count | identical per file |
| Text-only PDFs | 100% body parity |

Weakest files:

| File | Body parity | Caption exact |
| --- | ---: | ---: |
| `6 - Visual Design.md` | 72.8% | 0 |
| `1.2 - History of HCI.md` | 65.7% | 0 |
| `4.2 - Prototyping.md` | 82.3% | 0 |

PP-OCRv6 tiny does not preserve 95% parity on image-heavy slides. It matches digital text exactly on text-only PDFs, but reorders or rewrites OCR text and misclassifies some hand-drawn headings. PP-OCRv6 small was slower (108 s vs 86 s on `6 - Visual Design`) and did not improve body parity.

## Thread scaling

PP-OCRv4 CPU, same PDF, `DOCMD_OCR_THREADS` varied:

| Threads | Wall time |
| ---: | ---: |
| 1 | 26.6 s |
| 4 | 18.2 s |
| 8 | 20.3 s |
| 16 | 19.7 s |

Four threads were fastest in this run. The default is `min(4, cpu_count)` and can be overridden with `DOCMD_OCR_THREADS`.

## Test Sample Fixtures

Measurements taken on repository sample fixtures (`skills/docmd/references/fixtures/sample.{docx,pptx,pdf}`). Averaged over 2-3 iterations.

| Workload | Configuration | In-Process Mean | In-Process Min | CLI E2E Mean | CLI E2E Min | Markdown Size | Assets |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sample.docx` | No OCR | 88.7 ms | 24.8 ms | 0.251 s | 0.247 s | 0.2 KB | 1 files (7.1 KB) |
| `sample.pptx` | No OCR | 56.6 ms | 8.7 ms | 0.290 s | 0.287 s | 0.3 KB | 1 files (7.1 KB) |
| `sample.pdf` | No OCR | 590.3 ms | 12.2 ms | 1.425 s | 1.361 s | 0.1 KB | 1 files (7.1 KB) |
| `sample.pdf` | OCR (CPU, Cold) | 1239.8 ms | 1025.6 ms | 3.145 s | 3.114 s | 0.2 KB | 1 files (7.1 KB) |
| `sample.pdf` | OCR (CPU, Warm Engine) | 228.3 ms | 216.1 ms | - | - | 0.2 KB | 1 files (7.1 KB) |
| `Batch (3 files)` | Directory (No OCR, --jobs 1) | - | - | 1.629 s | 1.624 s | - | - |
| `Batch (3 files)` | Directory (No OCR, --jobs 2) | - | - | 1.498 s | 1.430 s | - | - |
| `Batch (3 files)` | Directory (With OCR, --jobs 1) | - | - | 3.245 s | 3.240 s | - | - |
| `Batch (3 files)` | Directory (With OCR, --jobs 2) | - | - | 3.252 s | 3.238 s | - | - |
| `sample.pdf (OCR Threads)` | 1 threads | - | - | 3.382 s | 3.334 s | - | - |
| `sample.pdf (OCR Threads)` | 2 threads | - | - | 3.226 s | 3.149 s | - | - |
| `sample.pdf (OCR Threads)` | 4 threads | - | - | 3.253 s | 3.242 s | - | - |
| `sample.pdf (OCR Threads)` | 8 threads | - | - | 3.304 s | 3.226 s | - | - |

## INF2002 Dataset Benchmark

Workload: 19 real-world university slide decks and assignment reports (18 PDFs, 1 DOCX, 579 total PDF pages, 394 unique extracted images, ~28 MB source data in `artifacts/scratch/INF2002/`).

### Directory Batch Conversion (No OCR)

End-to-end CLI execution time across all 19 documents:

| Configuration | Min Time | Mean Time | Throughput |
| :--- | ---: | ---: | ---: |
| Directory `--no-ocr --jobs 1` | 14.078 s | 14.220 s | 41.1 pages/s |
| Directory `--no-ocr --jobs 2` | 14.382 s | 14.421 s | 40.3 pages/s |
| Directory `--no-ocr --jobs 4` | 14.976 s | 15.269 s | 38.7 pages/s |

### Per-Document Warm Engine Profiling

Detailed in-process timings comparing digital extraction vs warm OpenVINO OCR and image caching across the corpus:

| Document | Pages / Size | Digital (No OCR) | Warm OCR Engine | Unique Images Cached |
| :--- | ---: | ---: | ---: | ---: |
| `1.1 - Introduction.pdf` | 59 p (2.8 MB) | 1.768 s | 47.721 s | +71 images |
| `1.2 - History of HCI.pdf` | 65 p (6.3 MB) | 3.295 s | 70.644 s | +53 images |
| `1.3 - User Centered Design.pdf` | 19 p (897 KB) | 0.355 s | 9.595 s | +19 images |
| `2.1 - Needfinding.pdf` | 37 p (1.4 MB) | 0.443 s | 11.000 s | +20 images |
| `2.2 - Task Analysis.pdf` | 30 p (819 KB) | 0.249 s | 6.246 s | +8 images |
| `3 - Usability Principles.pdf` | 68 p (3.5 MB) | 1.698 s | 40.701 s | +61 images |
| `4.1 - Ethics.pdf` | 24 p (1.3 MB) | 0.360 s | 6.803 s | +23 images |
| `4.2 - Prototyping.pdf` | 56 p (3.0 MB) | 1.030 s | 28.997 s | +31 images |
| `5 - Evaluation.pdf` | 83 p (2.2 MB) | 1.001 s | 33.021 s | +38 images |
| `6 - Visual Design.pdf` | 72 p (4.0 MB) | 1.911 s | 62.064 s | +57 images |
| `L1 - Design Sprint.pdf` | 2 p (54 KB) | 0.016 s | 0.009 s | +0 images |
| `L2 - Version Control with Git.pdf` | 34 p (943 KB) | 0.340 s | 6.333 s | +13 images |
| `T0 - As We May Think.pdf` | 3 p (49 KB) | 0.009 s | 0.007 s | +0 images |
| `T0A - As We May Think.pdf` | 9 p (91 KB) | 0.032 s | 0.031 s | +0 images |
| `T1 - UCD, Needfinding.pdf` | 2 p (43 KB) | 0.006 s | 0.005 s | +0 images |
| `T1A - UCD, Needfinding.pdf` | 7 p (75 KB) | 0.024 s | 0.023 s | +0 images |
| `T2 - Ethics and Prototypes.pdf` | 2 p (32 KB) | 0.005 s | 0.005 s | +0 images |
| `T2A - Ethics and Prototypes.pdf` | 7 p (80 KB) | 0.026 s | 0.027 s | +0 images |
| `studio3_individual_evaluation.docx` | 11 KB | 0.259 s | 0.054 s | +0 images |

### Directory Batch Conversion (With Warm OCR)

Full batch directory conversion with OCR enabled across all 579 pages and 417 extracted images:

| Configuration | Total Wall Time | Speedup vs jobs=1 |
| :--- | ---: | ---: |
| Directory `With OCR --jobs 1` (historical subprocess) | 387.51 s (6m 27s) | 1.00x |
| Directory `With OCR --jobs 2` (historical subprocess) | 443.97 s (7m 23s) | 0.87x (CPU core contention) |
| Directory `With OCR --jobs 4` (historical subprocess) | 330.27 s (5m 30s) | 1.17x (optimal parallel overlap) |
| Directory `With OCR + Layout --jobs 2` (in-process + verify) | 58.09 s (0m 58s) | 6.67x vs jobs=1 (warm shared worker pool) |
| Directory `With OCR + Layout --jobs 4` (in-process + verify) | 55.75 s (0m 55s) | 6.95x vs jobs=1 (warm shared worker pool) |

## Comparative Analysis: pdftotext vs docmd

Automated benchmark evaluating `pdftotext` (Poppler 26.10) against `docmd` on the 18 INF2002 PDFs:

| Metric | `pdftotext` (Poppler) | `docmd (--no-ocr)` | `docmd (warm OCR)` |
| :--- | :--- | :--- | :--- |
| **Execution Time (18 PDFs, 579 p)** | **1.048 s** | 27.234 s | 330.27 s |
| **Output Format** | Plain text (form feeds `\x0c`) | GitHub Flavored Markdown | GitHub Flavored Markdown |
| **Extracted Text Chars** | 156,564 | 31,152,406 (with assets) | 31,180,000+ |
| **Headings Inferred (`#` / `##`)** | 0 (unsupported) | 987 (font hierarchy) | 987 |
| **Images / Figures Extracted** | 0 (unsupported) | 417 (in `.assets/`) | 417 (with OCR captions) |
| **Scanned / UI Slides** | Blank `\x0c\x0c\x0c` | Embedded asset link | Embedded asset + caption |
| **Running Headers / Footers** | Retained (raw noise) | Stripped (heuristics) | Stripped (heuristics) |
| **DOCX / PPTX Support** | None (PDF only) | Yes (built-in) | Yes (built-in) |
| **Output Integrity Gate** | None | `--verify` (tables, links) | `--verify` (tables, links) |

## Takeaways

- Structurally identical images were OCR'd once after hashing, cutting onnxruntime OCR from 116.2 s to 47.6 s.
- Moving OCR to OpenVINO CPU cut the best observed time from 47.6 s to 17.6 s.
- PP-OCRv6 tiny on GPU is the fastest observed configuration at 13.8 s.
- PP-OCRv4 GPU was slower than CPU, but PP-OCRv6 GPU is faster; benchmark the chosen model per host.
- NPU is present, but PP-OCRv6 still fails NPU compile on driver 1.28.0 and falls back to GPU or CPU.
- Absolute times are load-sensitive; the loaded-host runs are 3-4x slower than the best runs.
- Sample fixtures convert in under 60 ms in-process for DOCX/PPTX, and ~228 ms for warm PDF OCR (~1.2 s cold).
- In batch conversions with OCR, warm worker thread pool with shared `OcrEngine` and `OcrCache` eliminated repeated model recompilations across files.
- On real-world slide corpora (579 pages, 394 images), `docmd` converts without OCR in 14.1 s (41 pages/s). With OCR, 4 workers achieved 330.27 s across all 394 images.
- Compared to `pdftotext`: `pdftotext` is ~25x faster for raw text dumps (1.05 s), but drops all 417 images, detects 0 headings, outputs 0 markdown, and cannot parse DOCX or PPTX.

## Corrective Pass: INF2002 1.1 (2026-11-09)

File-mode conversion of `1.1 - Introduction.pdf` (59 pages), measured after the
OCR merge, deduplication, layout, table, and link work. The baseline is the
reviewed `7f819b1` output from the addendum.

| Metric | Baseline docmd 7f819b1 | Corrective OCR | Corrective `--no-ocr` |
| :--- | ---: | ---: | ---: |
| Words | 5,466 | 3,738 | 1,723 |
| Unique words | 1,382 | 1,325 | 668 |
| Heading lines | 162 | 77 | 76 |
| Heading words | 871 | 286 | 281 |
| Table rows | 0 | 60 | 29 |
| Markdown links | 0 | 19 | 24 |
| Image files | 74 | 74 | 74 |
| Characters | 35,538 | 26,093 | 13,362 |

The word and character drop is expected: OCR lines matching digital text and
image captions matching the page body are now suppressed, and the previous
output emitted the Singapore Airlines fare text three times. Unique words are
within 4 percent of the baseline. Headings fall inside the 40-80 target and
links rise from 0 to 19 in OCR mode. Table rows rise from 0 to 60, above the
addendum's target of 40; the two OCR-schedule tables account for the increase.
The `--no-ocr` table count is 29 because those screenshots are not readable
without OCR. Run the local harness with
`uv run python artifacts/scripts/bench_metrics.py` after setting
`DOCMD_BENCH_DIR`.

### Full INF2002 Corpus

A full local run against `$HOME/Drive/gdrive/SIT/INF2002` on 2026-11-09 used
the harness with OCR enabled and the default CPU/tiny OCR configuration. The
corpus is course material and is not committed.

| Metric | Total |
| :--- | ---: |
| Documents converted | 36 |
| Words | 67,172 |
| Heading lines | 1,394 |
| Table rows | 517 |
| Markdown links | 118 |
| Images | 662 |
| OCR image-text blocks | 229 |
| Characters | 449,589 |
| Serial in-process time | 688.06 s |

The corpus contains one zero-byte `.docx` (`INF2002 STUDIO 3 - Synthesized
Final Report.docx`) which exits `2` and is skipped by the harness. An `.xlsx`
and a `.zip` are outside the supported extensions. The slowest documents were
`1.2 - History of HCI.pdf` (78.3 s), `6 - Visual Design.pdf` (76.4 s), and
`1.1 - Introduction.pdf` (64.0 s), all with OCR and layout enabled.
