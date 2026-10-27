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

## Takeaways

- Structurally identical images were OCR'd once after hashing, cutting onnxruntime OCR from 116.2 s to 47.6 s.
- Moving OCR to OpenVINO CPU cut the best observed time from 47.6 s to 17.6 s.
- PP-OCRv6 tiny on GPU is the fastest observed configuration at 13.8 s.
- PP-OCRv4 GPU was slower than CPU, but PP-OCRv6 GPU is faster; benchmark the chosen model per host.
- NPU is present, but PP-OCRv6 still fails NPU compile on driver 1.28.0 and falls back to GPU or CPU.
- Absolute times are load-sensitive; the loaded-host runs are 3-4x slower than the best runs.
