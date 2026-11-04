# Robustness Review: Batch & Verification (V04)

## Findings

### Finding 1: Running Worker Subprocesses Not Terminated on Batch Failure
- Current: `scripts/docmd:1256-1259`
- Gap: When a document fails in parallel directory conversion (`convert_directory`), `pending.cancel()` is called on all futures. In Python `concurrent.futures`, `Future.cancel()` only prevents unstarted tasks from starting; it cannot cancel futures already executing in worker threads. Furthermore, worker threads are blocked inside synchronous `subprocess.run(...)`. The `with ThreadPoolExecutor` context manager exits by calling `pool.shutdown(wait=True)`, which blocks indefinitely until all in-flight child processes exit on their own.
- Failure/impact: If a batch has long-running conversions (e.g. high-page-count PDF OCR) or a stalled process, `docmd` hangs indefinitely after detecting a fatal failure. In-flight child processes also continue writing files to disk and printing to stderr after the batch has aborted.
- Config / remediation: Manage `subprocess.Popen` instances directly, and send `proc.terminate()` to all active child processes when any future yields a non-zero exit code or an interrupt occurs.
- Source: `scripts/docmd:1243-1262`
- Default check: Calling `cancel()` on running future does not terminate child process; `ThreadPoolExecutor.__exit__` blocks until child process terminates.
- Confidence: High

### Finding 2: Non-Deterministic Exit Code Under Mixed Document Failures in Parallel Mode
- Current: `scripts/docmd:1253-1259`
- Gap: Directory conversion consumes worker results via `as_completed(futures)` and immediately returns `result.returncode` from the first future that completes with a non-zero exit code.
- Failure/impact: In batches containing multiple failing documents of different failure classes (e.g., corrupt document exiting 2, password error exiting 3, verify error exiting 1), exit codes are non-deterministic and timing-dependent. Single-job runs (`--jobs 1`) return the error code of the first document in alphabetical order, whereas parallel runs (`--jobs > 1`) return whichever child process finishes first.
- Config / remediation: Track results by input document order. When failures occur, return the error code corresponding to the first failing document in sorted document order.
- Source: `scripts/docmd:1231-1262`
- Default check: Scheduling order in `as_completed` determines which non-zero returncode is encountered first.
- Confidence: High

### Finding 3: Arbitrary Local Path Probing and Traversal Outside Output Bundle in Asset Verification
- Current: `scripts/docmd:281`
- Gap: `verify_markdown` resolves link destinations with `resolved = (base / unquote(link)).resolve()`. It does not verify that `resolved` is contained within `base` or an asset subfolder via `resolved.is_relative_to(base)`.
- Failure/impact: Filesystem oracle and broken distribution: documents with links like `![probe](/etc/shadow)` probe local paths. Links referencing files outside output bundle pass verification silently.
- Config / remediation: Enforce directory containment:
  ```python
  try:
      resolved.relative_to(base)
  except ValueError:
      errors.append(f"asset outside bundle: {target}")
  ```
- Source: `scripts/docmd:281-285`
- Default check: `verify_markdown('![passwd](/etc/passwd)', base)` produces 0 errors because `/etc/passwd` exists on the host.
- Confidence: High

### Finding 4: Unescaped Spaces in Link Destinations Silently Bypassed by Asset Verifier
- Current: `scripts/docmd:47-49`, `scripts/docmd:269-270`
- Gap: `LINK_RE` requires destinations not enclosed in `<...>` to match `([^)\s]+)`. If a markdown image or link destination contains an unescaped space (e.g., `![alt](missing image.png)`), the regex match fails entirely.
- Failure/impact: Broken or missing assets containing unescaped spaces are silently ignored by `verify_markdown`, falsely reporting 0 errors and passing verification.
- Config / remediation: Update regex or tokenizer to capture destinations containing spaces or flag unescaped whitespace.
- Source: `scripts/docmd:47-49`, `scripts/docmd:269-270`
- Default check: `verify_markdown('![test](missing image.png)', base)` returns `[]`, failing to detect missing asset.
- Confidence: High

### Finding 5: Parentheses in Filenames Truncated by `LINK_RE`, Causing False Missing Asset Errors
- Current: `scripts/docmd:48`
- Gap: In `LINK_RE`, destination group `([^)\s]+)` terminates at the first closing parenthesis `)`.
- Failure/impact: Any valid Markdown asset filename containing parentheses (e.g., `figure_(1).png`) is truncated at the closing parenthesis (`figure_(1`). Verification checks for the truncated path and emits a false-positive `missing asset: ...` error.
- Config / remediation: Support balanced parentheses in URL destinations or require `<...>` delimiters for URLs containing parentheses.
- Source: `scripts/docmd:47-49`, `scripts/docmd:269-285`
- Default check: `verify_markdown('![chart](charts/figure_(1).png)', base)` reports `['missing asset: charts/figure_(1']`.
- Confidence: High

### Finding 6: Unescaped Pipes Inside Inline Code Spans Trigger False Table Column Count Mismatch
- Current: `scripts/docmd:179-202`
- Gap: `split_table_row` splits on `|` whenever `not escaped`. It only handles backslash escaping (`\|`) and does not track inline backtick code spans.
- Failure/impact: GFM specification (section 4.10) states that code spans containing pipe characters (e.g., `| Type | `str | int` |`) are not table cell separators. `split_table_row` splits inside code spans, artificially inflating the cell count and raising a false-positive table column count mismatch.
- Config / remediation: Track inline backtick code spans in `split_table_row` and ignore `|` characters inside active code spans.
- Source: `scripts/docmd:179-202`, `scripts/docmd:245-249`
- Default check: `verify_markdown('| A | B |\n| --- | --- |\n| C | `D | E` |\n')` raises table column mismatch error.
- Confidence: High

### Finding 7: Escaped Trailing Pipe Truncated and Corrupted in `split_table_row`
- Current: `scripts/docmd:183-184`
- Gap: `split_table_row` removes trailing pipes using `if stripped.endswith("|"): stripped = stripped[:-1]` without checking if the pipe is preceded by an unescaped backslash (`\|`).
- Failure/impact: In table rows where outer boundary pipes are omitted and the last cell ends with an escaped pipe (`Col 1 | Col 2 \|`), the pipe is stripped and the trailing backslash remains, corrupting cell text.
- Config / remediation: Guard trailing pipe strip: `if stripped.endswith("|") and not stripped.endswith(r"\|"): stripped = stripped[:-1]`.
- Source: `scripts/docmd:183-184`
- Default check: `split_table_row(r"Col 1 | Col 2 \|")` produces `['Col 1', 'Col 2 \\']`.
- Confidence: High

### Finding 8: Code Fence Length and Nesting Depth Ignored in `fence_marker` and `verify_markdown`
- Current: `scripts/docmd:212-217`, `scripts/docmd:227-234`
- Gap: `fence_marker` tests `stripped.startswith(("```", "~~~"))` and returns fixed strings `"```"` or `"~~~"`. It does not record the character run length, does not enforce that closing fences must match or exceed opening fence length, and permits info strings on closing fences.
- Failure/impact: Outer multi-tick code fences nesting 3-backtick fences toggle tracking prematurely, causing spurious unbalanced fence or missing asset errors.
- Config / remediation: Store opening fence state as `(marker_char, marker_length)`. Close only when encountering the same character with length >= opening length and no trailing non-whitespace info string.
- Source: `scripts/docmd:212-217`, `scripts/docmd:220-254`
- Default check: ` ````markdown\n```\n```` ` raises `unbalanced code fence`.
- Confidence: High

### Finding 9: Output and Asset Directory Collisions for Same-Stem Input Files
- Current: `scripts/docmd:1158-1160`, `scripts/docmd:1246-1251`
- Gap: `document_output_path` maps any input file to `{stem}.md` and `{stem}.assets/`. When an input directory contains multiple supported documents sharing the same stem (e.g. `report.docx` and `report.pdf`), both target the exact same output path.
- Failure/impact: Overwrite and data loss in single-job mode; race conditions and corrupt outputs in parallel mode.
- Config / remediation: Detect stem collisions in `discover_documents` and fail early with an informative collision error.
- Source: `scripts/docmd:1158-1160`, `scripts/docmd:1235`, `scripts/docmd:1246`
- Default check: Input directory containing `sample.docx` and `sample.pdf` targets identical output paths.
- Confidence: High

### Finding 10: Unhandled Filesystem Errors on Output Directory and Markdown File Writes
- Current: `scripts/docmd:1083-1102`, `scripts/docmd:1197`, `scripts/docmd:1296`
- Gap: Subsequent filesystem writes in `write_markdown` and `output.read_text()` in `convert_one` are unguarded.
- Failure/impact: Read-only directories or disk exhaustion (`ENOSPC`) cause unhandled Python tracebacks rather than clean `docmd: error: cannot write output: ...` messages.
- Config / remediation: Wrap `write_markdown` and `output.read_text` invocations in `try ... except OSError as exc:`.
- Source: `scripts/docmd:1083-1102`, `scripts/docmd:1197`, `scripts/docmd:1296-1300`
- Default check: Read-only output directory raises uncaught `PermissionError`.
- Confidence: High

### Finding 11: Single-Column GFM Tables Excluded from Column Count Verification
- Current: `scripts/docmd:207`
- Gap: `is_table_delimiter` requires `len(cells) > 1 and all(...)`.
- Failure/impact: Standard GFM single-column tables bounded by outer pipes are rejected as non-delimiters. Column count mismatches in subsequent rows are silently bypassed.
- Config / remediation: Allow single-column delimiter rows when bounded by outer pipes: `len(cells) >= 1 and ("|" in line)`.
- Source: `scripts/docmd:205-210`
- Default check: `is_table_delimiter('| --- |')` returns `False`.
- Confidence: High

## Failure modes
- Process Hang on Batch Failure: `ThreadPoolExecutor.__exit__` blocks waiting for child processes that `Future.cancel()` cannot terminate.
- Race Conditions & File Corruption: Input documents sharing identical stems collide on `{stem}.md` and `{stem}.assets/`.
- Local Filesystem Probing: Asset verification resolves arbitrary absolute and relative `../` link destinations against host filesystem without sandbox boundaries.
- Silent Asset Verification Bypass: Asset links containing unescaped spaces are ignored by `LINK_RE`.
- False Verification Errors: Pipes inside inline code spans trigger false table column mismatch errors; nested fences trigger false unbalanced fence errors; parentheses in filenames trigger false missing asset errors.
- Exit Code Non-Determinism: Parallel batch runs return the exit code of whichever failure finishes first in real time.
- Unhandled Filesystem Crashes: Read-only directories or disk full errors in `write_markdown` raise uncaught `OSError` tracebacks.

## Seams
- Batch Discovery Seam: `discover_documents` filters non-hidden supported files (`.docx`, `.pptx`, `.pdf`) and prunes nested output roots.
- Worker Execution Seam: `convert_directory` orchestrates in-process worker pool (`ThreadPoolExecutor`, `--jobs N`) calling `convert_one` with shared `ocr_engine` and `OcrCache`.
- Verification Scanner Seam: `verify_markdown` separates table structure validation from asset link extraction.
- Asset Extraction Seam: `write_markdown` extracts base64 data URIs into sibling `<stem>.assets/` directories.
- Table Row Tokenizer Seam: `split_table_row` parses delimiter and data rows into individual cells.

## Rejected defaults
- Cooperative Subprocess Cancellation: Relying on `Future.cancel()` to abort running child processes.
- Unbounded Path Resolution in Link Verification: Allowing `Path.resolve()` to navigate outside the document output root.
- Unbracketed Link Parsing on Whitespace: Assuming link targets without angle brackets never contain spaces.
- Pipe Splitting Ignorant of Code Spans: Assuming pipe `|` characters in Markdown tables are always cell separators.
- Flat Fence State Toggle: Assuming all code fences start and end with exactly 3 characters.
- Stem-Only Output Naming: Assuming all discoverable documents within a directory tree have globally unique stems.

## Open Questions
None.
