# Robustness Review: Media & OCR (V03)

## Findings

### Finding 1: Unhandled OCR Exceptions on Corrupted/Unsupported Images Crash Entire Document Conversion
- Current: `scripts/docmd:832` (`extract_pdf_lines`), `scripts/docmd:911` (`pdf_image_blocks`)
- Gap: Calls to `ocr_image_text(ocr_engine, image)` and `ocr_pdf_page(page, ocr_engine)` have no error boundaries (`try...except`). When PDF images use formats unsupported by PIL/RapidOCR (e.g. JBIG2, JPX, 1-byte truncated streams), or if OpenVINO/RapidOCR raises `PIL.UnidentifiedImageError` or `cv2.error`, the exception bubbles unhandled.
- Failure/impact: A single corrupt or unsupported image or page pixmap aborts conversion for the entire document with exit code 1 instead of continuing with digital text and raw image links.
- Config / remediation: Wrap OCR calls in `try ... except Exception:` and fall back to empty string / digital text.
- Source: `scripts/docmd:832`, `scripts/docmd:911`
- Default check: Fails unsafe; `options.use_ocr=True` is the default for PDF processing.
- Confidence: High

### Finding 2: Ineffective Hardware Accelerator Patching Due to RapidOCR Lazy Compilation
- Current: `scripts/docmd:312-328`, `scripts/docmd:343-347` (`_build_ocr_engine`)
- Gap: `Core.compile_model = patched_compile` is active only during `RapidOCR(params=params)` constructor execution. `RapidOCR` instantiates `TextDetector` and `TextRecognizer` lazily on first inference call `__call__`. By the time `engine(data)` runs, the `finally` block at line 347 has already restored `Core.compile_model = original_compile`.
- Failure/impact: `_accelerator_compile` is dead code; it is called 0 times. `DOCMD_OCR_DEVICE=gpu` or `DOCMD_OCR_DEVICE=npu` silently fails to use accelerator hardware and always executes on CPU.
- Config / remediation: Trigger warmup inference while `patched_compile` is active before restoring `original_compile`.
- Source: `scripts/docmd:320-327`, `scripts/docmd:343-347`
- Default check: Default device is `"auto"`, which falls back to CPU; users configuring GPU/NPU receive no error and no acceleration.
- Confidence: High

### Finding 3: Non-Thread-Safe OCR Engine and Class-Level Monkeypatching
- Current: `scripts/docmd:343-347` (`_build_ocr_engine`), `scripts/docmd:355-358` (`OcrEngine.__call__`)
- Gap: Process-global class mutation (`Core.compile_model = patched_compile`) lacks mutex synchronization. `OcrEngine.__call__` lazy initialization is unsynchronized. Furthermore, `RapidOCR.__call__` mutates internal state and delegates to an OpenVINO `InferRequest`, which is strictly not thread-safe.
- Failure/impact: Programmatic concurrent use of `OcrEngine` across threads causes state corruption, race conditions during compile patching, or OpenVINO segfaults.
- Config / remediation: Guard `OcrEngine.__call__` with `threading.Lock()` or isolate engines per-thread (`threading.local()`).
- Source: `scripts/docmd:343`, `scripts/docmd:355-358`
- Default check: CLI uses multiprocessing for `--jobs > 1`, but in-process callers have no concurrency protection.
- Confidence: High

### Finding 4: Confidence Score Filter Bypassed by `NaN` Values
- Current: `scripts/docmd:760` (`ocr_pdf_page`), `scripts/docmd:787` (`ocr_image_text`)
- Gap: The filter `if not text or (score is not None and score < 0.5): continue` relies on `score < 0.5`. In IEEE 754 floating point, `float('nan') < 0.5` is `False`.
- Failure/impact: Any OCR detection with `NaN` confidence passes through the filter and is emitted into document text and image captions.
- Config / remediation: Use `if not text or score is None or math.isnan(score) or score < 0.5: continue`.
- Source: `scripts/docmd:760`, `scripts/docmd:787`
- Default check: Fails open for `NaN` scores under default threshold 0.5.
- Confidence: High

### Finding 5: Inconsistent Thread Defaults Between Constructor and Environment Loader
- Current: `scripts/docmd:143` (`OcrConfig.__init__`), `scripts/docmd:154-156` (`OcrConfig.from_env`)
- Gap: `OcrConfig.__init__` defaults `threads: int = 0`. When `threads == 0`, line 340 skips setting `params["EngineConfig.openvino.inference_num_threads"]`, causing OpenVINO to allocate threads for all CPU cores on the host. In contrast, `from_env()` defaults to `min(4, os.cpu_count() or 1)`.
- Failure/impact: Code instantiating `OcrConfig()` directly spawns unbounded inference threads (e.g. 64-128 threads on server systems), causing CPU starvation and high context-switching overhead.
- Config / remediation: Set `threads: int = min(4, os.cpu_count() or 1)` in `OcrConfig.__init__`.
- Source: `scripts/docmd:143`, `scripts/docmd:155`
- Default check: Default constructor value `threads=0` fails unsafe.
- Confidence: High

### Finding 6: Unbounded In-Memory OCR Digest Cache in Batch Directory Conversion
- Current: `scripts/docmd:875-884`, `scripts/docmd:909-911` (`pdf_image_blocks`), `scripts/docmd:1233` (`convert_directory`)
- Gap: In single-job directory conversions (`--jobs 1`), `ocr_cache: dict[str, str] = {}` persists across all documents in the directory tree with no max size, TTL, or LRU eviction policy.
- Failure/impact: A batch conversion of thousands of documents containing tens of thousands of unique images accumulates unbounded strings in memory.
- Config / remediation: Enforce an upper bound (e.g. max 1,000 entries) or use an LRU cache.
- Source: `scripts/docmd:1233`, `scripts/docmd:910-911`
- Default check: Defaults to unbounded memory accumulation during `--jobs 1` directory conversions.
- Confidence: High

### Finding 7: DOCX Missing Relation ID Unhandled and Zero-Byte Assets
- Current: `scripts/docmd:615-617` (`convert_docx`), `scripts/docmd:666` (`convert_pptx`), `scripts/docmd:1098` (`write_markdown`)
- Gap: `convert_docx` indexes `document.part.related_parts[relation_id]` without checking key existence. DOCX and PPTX base64-encode empty `image.blob` (0 bytes). `write_markdown` writes a 0-byte file, causing subsequent `--verify` failures (`zero-byte asset`).
- Failure/impact: Missing relation IDs raise uncaught `KeyError`; 0-byte embedded images write empty assets that fail validation gates.
- Config / remediation: Validate `image is not None and len(image.blob) > 0` before emitting.
- Source: `scripts/docmd:615-617`, `scripts/docmd:1098`
- Default check: Verification gate flags 0-byte assets, but missing relation crashes DOCX conversion beforehand.
- Confidence: High

### Finding 8: Potential Division by Zero in `ocr_pdf_page`
- Current: `scripts/docmd:753-754` (`ocr_pdf_page`)
- Gap: `scale_x = page.rect.width / pixmap.width` and `scale_y = page.rect.height / pixmap.height` perform direct division without checking `pixmap.width > 0` and `pixmap.height > 0`.
- Failure/impact: A corrupted or zero-dimension PDF page pixmap causes an unhandled `ZeroDivisionError`, crashing document conversion.
- Config / remediation: Guard with `if not pixmap or pixmap.width == 0 or pixmap.height == 0: return []`.
- Source: `scripts/docmd:753-754`
- Default check: Fails unsafe on degenerate page dimensions.
- Confidence: High

### Finding 9: Discarded Compiler Config in Accelerator Compilation
- Current: `scripts/docmd:301` (`_accelerator_compile`), `scripts/docmd:315-327` (`patched_compile`)
- Gap: When `patched_compile` receives `compile_config`, `_accelerator_compile` invokes `compile_model(core, model, device_name=device)` without `compile_config`, while CPU fallback passes `config=compile_config`.
- Failure/impact: Accelerator compilation discards backend tuning and compilation options passed by RapidOCR.
- Config / remediation: Forward `config=compile_config` in `_accelerator_compile`.
- Source: `scripts/docmd:301`, `scripts/docmd:318`
- Default check: Incomplete parameter propagation to hardware backend.
- Confidence: High

### Finding 10: Missing Document Image Formats in MIME and Extension Mappings
- Current: `scripts/docmd:33-42` (`IMAGE_MIME_TYPES`), `scripts/docmd:1043-1051` (`IMAGE_EXTENSIONS`)
- Gap: Neither map supports common document image formats such as WMF (`image/x-wmf`), EMF (`image/x-emf`), JPEG 2000 (`image/jp2`, `image/jpx`), or JBIG2 (`image/jbig2`).
- Failure/impact: Assets are extracted with `.bin` extensions (`image-001.bin`). Markdown viewers fail to render them as inline images.
- Config / remediation: Add WMF, EMF, and JPX entries to both mappings.
- Source: `scripts/docmd:33`, `scripts/docmd:1043`
- Default check: Defaults to `.bin`, rendering degraded output in Markdown renderers.
- Confidence: Medium

## Failure modes
- UnidentifiedImageError on Corrupt/Exotic PDF Images: Unsupported format or corrupt payload aborts entire document conversion.
- Crash on Damaged PDF Page during Pixmap Generation / OCR: Zero dimensions or MuPDF pixmap errors crash conversion.
- Silent Accelerator No-Op: Setting `DOCMD_OCR_DEVICE=gpu` silently falls back to CPU due to deferred RapidOCR model compilation.
- Thread Contention / CPU Starvation: Direct `OcrConfig()` calls default to unbounded threads across host cores.

## Seams
- Converters -> `DATA_URI_RE` -> `write_markdown`: Converters emit `![](data:<mime>;base64,<payload>)`.
- `extract_pdf_lines` / `pdf_image_blocks` -> `load_ocr_engine`: Engine is passed down from `convert_pdf`.
- Layout Engine Seam: `load_layout_engine` loads thread-safe `LayoutEngine` (PP-Structure ONNX); `extract_layout_blocks` and `order_lines_by_layout` sort multi-column text lines.
- OCR Cache Seam: Mutex-protected `OcrCache` bounds digest caching at 1,000 items and shares results across directory workers.
- `ocr_items` -> `RapidOCR`: Decouples output normalization between tuple `(boxes, texts, scores)` and `RapidOCROutput`.

## Rejected defaults
- `threads = 0` in `OcrConfig.__init__`: Rejected in favor of explicit `min(4, os.cpu_count() or 1)`.
- Fail-Open NaN Confidence Scores: Rejected in favor of explicit `not (score >= 0.5)` or `math.isnan` guards.
- Unbounded Process-Lifetime `ocr_cache`: Rejected in favor of a bounded cache.

## Open Questions
None.
