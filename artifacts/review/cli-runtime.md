# Robustness Review: CLI & Runtime (V01)

## Findings

### Finding 1: Plaintext Document Password Exposed via CLI Subprocess Arguments in Parallel Batch Conversion
- Current: `scripts/docmd:1178-1179`, `scripts/docmd:1248-1250`
- Gap: When batch converting a directory with `jobs > 1` (default is `2`), `document_command()` builds child command lines with `["--password", options.password]` and passes them to `subprocess.run()`.
- Failure/impact: Plaintext passwords for encrypted documents are visible to all local users via `ps`, `/proc/<pid>/cmdline`, process accounting, and auditing logs.
- Config / remediation: Pass password via environment variable (e.g. `DOCMD_PASSWORD` in `os.environ` passed to `env=` in `subprocess.run`) or via stdin pipe, rather than command-line arguments.
- Source: Security leaks / secret confinement check.
- Default check: Yes, default `--jobs 2` invokes subprocesses with plaintext `--password` whenever a password is provided.
- Confidence: High

### Finding 2: Subprocess Execution in ThreadPool Lacks Timeout and Active Process Cancellation
- Current: `scripts/docmd:1248-1258`
- Gap: `subprocess.run()` is called without a `timeout`. When any task fails (`result.returncode != 0`), `pending.cancel()` is called on `Future` objects. In Python's `ThreadPoolExecutor`, `cancel()` only cancels pending (queued) tasks; it cannot cancel threads already executing `subprocess.run()`. Furthermore, exiting `with ThreadPoolExecutor(...)` invokes `shutdown(wait=True)`, blocking the main thread until all active subprocesses finish.
- Failure/impact: If a child process hangs on a malformed file or OCR freeze, `docmd` hangs indefinitely. On partial failure, `docmd` stalls waiting for all active workers to complete instead of terminating promptly.
- Config / remediation: Track spawned child `subprocess.Popen` instances and call `proc.terminate()` on failure/cancellation, or pass explicit timeouts to worker executions.
- Source: Explicit timeouts, retries, idempotency, and cancellation check.
- Default check: Yes, default `--jobs 2` runs multi-worker ThreadPoolExecutor on directory inputs.
- Confidence: High

### Finding 3: Verification Failure Leaves Invalid Markdown and Extracted Assets on Disk
- Current: `scripts/docmd:1200-1204`, `scripts/docmd:1296-1301`
- Gap: Both `convert_one()` and `main()` write output files and extract binary assets to disk via `write_markdown()` before executing `report_verify_errors()`. When verification fails, `docmd` emits errors and returns exit code `1`, but leaves the unverified/invalid output markdown and asset directories on disk.
- Failure/impact: Partial failure leaves broken state. Downstream tools or build systems checking for file presence will consume corrupt or invalid markdown files despite the non-zero exit code.
- Config / remediation: Write output files and assets to a temporary staging path and atomically promote them only upon successful verification; or unlink `output` and remove asset directory when verification fails.
- Source: Partial failure cannot leave half-written or unrecoverable state check.
- Default check: Triggers whenever `--verify` is passed and verification fails.
- Confidence: High

### Finding 4: Unhandled OSError / IsADirectoryError / PermissionError on File Output Crashes CLI with Python Traceback
- Current: `scripts/docmd:1290-1296`, `scripts/docmd:1083-1089`, `scripts/docmd:1200-1202`
- Gap: In single-file mode (`main()`), `out = Path(args.out)` classifies the path as a file if `out.suffix` is non-empty. If `args.out` is an existing directory with a dot in its name (e.g. `-o my.dir`), `main()` sets `output = out`, and `output.write_text()` raises an unhandled `IsADirectoryError`. Additionally, permission failures during directory creation or file writing are not caught.
- Failure/impact: Python traceback dumped to stderr instead of a structured single-line CLI error diagnostic (`docmd: error: ...`) with exit code 1.
- Config / remediation: Check `if out.is_dir(): output = out / f"{source.stem}.md"`. Wrap file output and directory creation in `try ... except OSError as exc:`.
- Source: Error boundary and hostile/invalid input check.
- Default check: Triggers whenever `-o` points to an existing directory containing a dot or a non-writable destination.
- Confidence: High

### Finding 5: Unhandled BrokenPipeError on Stdout Write Dumps Python Traceback
- Current: `scripts/docmd:1286-1288`
- Gap: In `main()`, `sys.stdout.write(markdown or "")` is executed directly without handling `BrokenPipeError` when `--stdout` is set.
- Failure/impact: Piping stdout to commands like `head -n 1` or an early-closing pipe crashes `docmd` with an unhandled `BrokenPipeError` traceback on stderr.
- Config / remediation: Wrap standard output write in a try/except block catching `BrokenPipeError` and exit cleanly.
- Source: Robustness, error boundary, and pipe handling check.
- Default check: Triggers whenever `docmd <input> --stdout` is piped to a tool that exits before consuming full output.
- Confidence: High

### Finding 6: Filesystem Permission and Missing File Errors in Format Openers Misclassified as CorruptDocumentError (Exit Code 2)
- Current: `scripts/docmd:390-391`, `scripts/docmd:399-400`, `scripts/docmd:1121-1126`, `scripts/docmd:1144-1146`
- Gap: `open_office_source` catches generic `Exception as exc` and re-raises `CorruptDocumentError`. `open_pdf` catches `pymupdf.FileDataError` (which PyMuPDF raises on `PermissionError`) and raises `CorruptDocumentError`. When a file is unreadable (e.g. `chmod 000`) or missing during `convert_source()`, `docmd` misclassifies the OS permission/I/O error as a corrupted document, and `exit_code_for` returns exit code 2 instead of 1.
- Failure/impact: Violates documented exit code contract (`1` CLI/runtime failure, `2` corrupt document). Automation treats permission or I/O failures as corrupt documents.
- Config / remediation: Exempt `(PermissionError, FileNotFoundError, OSError)` from `CorruptDocumentError` wrapping.
- Source: Exit code contract / boundary error classification.
- Default check: Yes, any file lacking read permission exits with code 2 instead of 1.
- Confidence: High

### Finding 7: File Stem Collisions in Directory Input Silently Overwrite Output and Clashing Assets
- Current: `scripts/docmd:1158-1160`, `scripts/docmd:1235`, `scripts/docmd:1246`
- Gap: `document_output_path(out, source, document)` maps every input to `out / relative.parent / f"{relative.stem}.md"`. If an input directory contains multiple files with the same stem and different supported extensions (e.g. `guide.docx` and `guide.pdf`), both target `guide.md` and share `guide.assets/`.
- Failure/impact: In sequential mode (`--jobs 1`), the latter file silently overwrites the former, causing data loss. In parallel mode (`--jobs 2+`), concurrent subprocesses race to write to the same output file and asset directory, resulting in corrupted output.
- Config / remediation: Validate stem collisions after `discover_documents()`. Disambiguate destination filenames or abort early with an error before initiating conversion.
- Source: Concurrency, ordering, and duplicate delivery check.
- Default check: Triggers on any directory containing multiple supported formats with the same stem.
- Confidence: High

### Finding 8: Non-Deterministic Output Ordering and Interleaved Subprocess Errors in Multi-Worker Directory Mode
- Current: `scripts/docmd:1243-1262`
- Gap: In single-worker mode (`jobs=1`), documents are converted in deterministic sorted order (`sorted(documents)`). In multi-worker mode (`jobs >= 2`, default is 2), tasks are submitted to `ThreadPoolExecutor`, and `as_completed(futures)` processes completions in non-deterministic order. Progress logging (`docmd: wrote ...`) order varies across runs. If multiple documents fail with different errors, the final exit code is non-deterministic (determined by whichever child subprocess finishes first). Additionally, child subprocess stderr is unbuffered and uncaptured, causing concurrent child error logs to interleave.
- Failure/impact: Flaky CI runs, non-reproducible exit codes, and garbled error output on stderr.
- Config / remediation: Order results deterministically before reporting progress or errors, and capture child process stderr to stream output atomically per document.
- Source: Concurrency, ordering, and duplicate delivery check.
- Default check: Yes, default `--jobs 2` produces non-deterministic completion order.
- Confidence: High

### Finding 9: Empty String Input Path Bypasses Validation and Resolves to Current Working Directory
- Current: `scripts/docmd:1271-1277`
- Gap: In Python, `Path("")` evaluates to `Path(".")`. When `docmd ""` is called without flags, `source.exists()` and `source.is_dir()` evaluate to True. An empty string argument is not rejected as invalid; instead, `docmd` starts recursively converting the entire current working directory into `./out/`.
- Failure/impact: Accidental invocation `docmd ""` silently triggers a full conversion of the entire current repository/workspace.
- Config / remediation: Validate `if not args.input_path or not args.input_path.strip():` in `main()`.
- Source: Reject invalid, missing, and hostile input at boundary.
- Default check: Yes, `docmd ""` initiates recursive conversion of cwd instead of exiting 1.
- Confidence: High

### Finding 10: Inconsistent Invariant Validation for `jobs` Between ArgumentParser, ConversionOptions, and ThreadPoolExecutor
- Current: `scripts/docmd:106-124`, `scripts/docmd:1267-1269`, `scripts/docmd:1243`
- Gap: `build_parser` sets `default=2`, while `ConversionOptions.__init__` sets `jobs: int = 1`. Invariant validation for `jobs < 1` is performed in `main()` after parsing rather than inside `ConversionOptions` or `DocmdArgumentParser`. Programmatic instantiation of `ConversionOptions(jobs=0)` bypasses CLI validation and crashes `ThreadPoolExecutor` with `ValueError: max_workers must be greater than 0`.
- Failure/impact: Inconsistent defaults between programmatic and CLI usage; internal unhandled ValueError on invalid job count.
- Config / remediation: Enforce invariant in `ConversionOptions.__init__`.
- Source: Defaults fail safe / invariant boundary check.
- Default check: Programmatic calls with `jobs=0` bypass CLI check and crash thread pool.
- Confidence: High

## Failure modes
- Subprocess stall / deadlock: when `--jobs >= 2` processes a document that hangs indefinitely, `subprocess.run` has no timeout, and the parent process hangs forever.
- Premature cancel deadlock: when a worker fails with non-zero exit code in parallel mode, `ThreadPoolExecutor.__exit__` calls `shutdown(wait=True)`, causing `docmd` to block waiting for all other active subprocesses to finish.
- Stem collision data loss: multiple files in the same directory sharing a stem target the exact same output path `doc.md` and asset folder `doc.assets/`.
- Stale and orphan asset accumulation: repeated conversions into the same output directory do not clean up previously extracted assets.
- Partial write on verification failure: when verification fails (`--verify`), the invalid output markdown and extracted assets remain on disk.
- Pipeline broken pipe crash: writing to a closed stdout pipe (`--stdout | head -n 1`) raises uncaught `BrokenPipeError` with Python traceback.
- Output destination is directory: passing an existing directory with a dot in its name causes `main` to classify it as a file by suffix, resulting in `IsADirectoryError`.
- Misclassified permission errors: unreadable files (`chmod 000`) cause `CorruptDocumentError` (exit code 2) instead of runtime failure (exit code 1).

## Seams
- CLI / Subprocess Boundary: `document_command()` serializes CLI flags to invoke `scripts/docmd` as a child process, exposing `--password` in `sys.argv`.
- Programmatic vs CLI Boundary: `convert_source()` and `ConversionOptions` are exposed as Python functions/classes with differing invariant checks from `main()`.
- Conversion to Markdown / Asset Extraction Seam: `write_markdown()` extracts base64 data URIs into sibling `<stem>.assets/` directories without atomic staging.
- Verification Seam: `verify_markdown()` verifies against filesystem paths (`base_dir`), evaluating relative links against `Path.cwd()` in stdout mode instead of source directory.

## Rejected defaults
- `jobs=2` by default: parallel execution spawns child subprocesses by default on directory inputs, exposing `--password` via `argv` and introducing non-deterministic completion ordering.
- Classification of `-o` by `Path.suffix`: any directory path containing a dot is mistakenly classified as a target file path.
- In-place writing before verification: writing directly to target paths and then verifying leaves corrupt files on disk when verification fails.
- Catch-all exception handling in format openers: converting all generic `Exception` occurrences into `CorruptDocumentError` masks I/O and permission issues.

## Open Questions
None.
