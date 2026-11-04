# Robustness Review: Document Parsing (V02)

## Findings

### Finding 1: Unhandled KeyError on Missing Heading Styles in DOCX
- Current: `scripts/docmd:571`
- Gap: `convert_docx` assumes styles `Heading 1` through `Heading 6` are present in `document.styles`. Non-English Word documents (where headings are localized e.g. "Titre 1", "Überschrift 1", or not predefined) raise `KeyError`.
- Failure/impact: Any DOCX file lacking any of `Heading 1`..`Heading 6` crashes immediately with `KeyError: "no style with name 'Heading 1'"` and exits with code 1 instead of converting the document.
- Config / remediation: Wrap style lookup in `try ... except KeyError:`.
- Source: `scripts/docmd:569-574`
- Default check: Yes, DOCX with stripped styles element crashes with `KeyError`.
- Confidence: High

### Finding 2: Infinite Loop on Cyclic Style Inheritance in DOCX
- Current: `scripts/docmd:507-512`, `scripts/docmd:526-529`
- Gap: `style_size` and `is_bold` traverse `style.base_style` using `while style is not None:` without tracking visited styles or capping recursion depth.
- Failure/impact: Malformed DOCX with circular `w:basedOn` style inheritance (e.g. Style A -> Style B -> Style A) causes an infinite loop that freezes the process at 100% CPU (Denial of Service).
- Config / remediation: Maintain a `visited` set or recursion depth bound.
- Source: `scripts/docmd:507-512`, `scripts/docmd:526-529`
- Default check: Creating circular `base_style` references causes `convert_docx` to hang indefinitely.
- Confidence: High

### Finding 3: Crash on Missing "Normal" Style When Body Sizes Are Empty in DOCX
- Current: `scripts/docmd:567`
- Gap: When `body_sizes` is empty (e.g. document containing only tables, images, or headings), `convert_docx` looks up `document.styles["Normal"]`.
- Failure/impact: In localized Word documents or custom templates lacking a style named "Normal", line 567 raises `KeyError: "no style with name 'Normal'"`.
- Config / remediation: Safely query `document.styles` with fallback default font size 11.0.
- Source: `scripts/docmd:564-568`
- Default check: Tested DOCX with only a table and removed "Normal" style; crashed with `KeyError`.
- Confidence: High

### Finding 4: Crash on Missing Notes Text Frame in PPTX
- Current: `scripts/docmd:670`
- Gap: Assumes `slide.notes_slide.notes_text_frame` is non-None whenever `slide.has_notes_slide` is True.
- Failure/impact: In PPTX presentations where a slide has a notes slide but its body text placeholder shape was removed, `notes_slide.notes_text_frame` is `None`. Calling `.text` raises `AttributeError: 'NoneType' object has no attribute 'text'`.
- Config / remediation: Guard against `None` on `getattr(slide.notes_slide, "notes_text_frame", None)`.
- Source: `scripts/docmd:669-672`
- Default check: PPTX slide with deleted notes placeholder causes `AttributeError`.
- Confidence: High

### Finding 5: AttributeError on Paragraphs With Missing or None Style in DOCX
- Current: `scripts/docmd:545`, `scripts/docmd:549`, `scripts/docmd:605`
- Gap: Direct attribute access `(paragraph.style.name or "").lower()` assumes `paragraph.style` is always an object.
- Failure/impact: If `styles.xml` is empty, stripped, or paragraph properties reference an undefined style, `paragraph.style` returns `None`. Accessing `.name` crashes with `AttributeError`.
- Config / remediation: Use safe attribute access `(getattr(paragraph.style, "name", "") or "").lower()`.
- Source: `scripts/docmd:544-556`, `scripts/docmd:604-607`
- Default check: Paragraph with `p.style is None` verified crashing with `AttributeError`.
- Confidence: High

### Finding 6: Multi-Column Reading Order Collapses on Spanning Header / Banner in PDF
- Current: `scripts/docmd:717-728`
- Gap: `order_pdf_lines` merges clusters if `cluster_x0 < previous_x1`. When a multi-column page contains a wide element (e.g. top title, banner, horizontal rule) spanning across columns, `previous_x1` overlaps the right column's `x0`, merging all columns into a single cluster.
- Failure/impact: The clustering collapses and falls back to simple Y-sorting, interleaving lines horizontally across columns.
- Config / remediation: Separate wide spanning lines (width > 60% of page width) prior to column clustering, then re-insert into reading order by Y-bounds.
- Source: `scripts/docmd:700-735`
- Default check: Verified multi-column page with title interleaves columns.
- Confidence: High

### Finding 7: Paragraph Breaks Erased Between Same-Sized Paragraphs in PDF
- Current: `scripts/docmd:990-1008`
- Gap: `convert_pdf` only flushes the current paragraph accumulator when `line["page"] != current_page` or `heading_levels.get(line["size"]) is not None`. It does not detect vertical gaps between lines or respect PyMuPDF block boundaries.
- Failure/impact: Distinct paragraphs sharing the body font size on the same page are joined with a space into a single monolithic paragraph, destroying paragraph formatting.
- Config / remediation: Flush paragraph buffer when vertical distance between consecutive lines exceeds standard line spacing.
- Source: `scripts/docmd:987-1009`
- Default check: Verified PDF with two paragraphs separated by vertical gap merged into a single block.
- Confidence: High

### Finding 8: PPTX Content and Pictures Inside Group Shapes Silently Dropped
- Current: `scripts/docmd:643-667`
- Gap: `convert_pptx` iterates only over top-level `slide.shapes`. A `GroupShape` has `has_text_frame == False` and `has_table == False`. The converter does not inspect child shapes in `shape.shapes`.
- Failure/impact: All text frames, tables, and images placed inside PowerPoint group shapes are silently dropped from markdown output.
- Config / remediation: Recursively traverse child shapes if `shape.shape_type == MSO_SHAPE_TYPE.GROUP`.
- Source: `scripts/docmd:643-667`
- Default check: Group shape containing a text frame is skipped in slide shapes loop.
- Confidence: High

### Finding 9: Unhandled KeyError on Missing Image Relationship in DOCX
- Current: `scripts/docmd:615`
- Gap: `image = document.part.related_parts[relation_id]` directly accesses `related_parts` without checking if `relation_id` exists.
- Failure/impact: If an `a:blip` element references an external target or has an invalid relationship ID, `convert_docx` crashes with `KeyError` (exit code 1) instead of skipping the invalid image.
- Config / remediation: Guard dictionary access with `if relation_id not in document.part.related_parts: continue`.
- Source: `scripts/docmd:611-616`
- Default check: python-docx raises `KeyError` when relationship ID is missing from `related_parts`.
- Confidence: High

### Finding 10: Nested Tables in DOCX Silently Omitted
- Current: `scripts/docmd:618-623`
- Gap: `rows = [[cell.text for cell in row.cells] for row in block.rows]` uses `cell.text`, extracting only text from paragraphs directly within the cell, completely ignoring `cell.tables`.
- Failure/impact: Any table nested within another table's cell is silently dropped from the generated markdown.
- Config / remediation: Check `cell.tables` or use `cell.iter_inner_content()` to serialize nested tables.
- Source: `scripts/docmd:618-623`
- Default check: Nested table in cell omitted by `cell.text`.
- Confidence: High

### Finding 11: Duplicate Extraction of Shared / Header Images Across PDF Pages
- Current: `scripts/docmd:888-893`
- Gap: `seen: set[int] = set()` in `pdf_image_blocks` is re-initialized inside the `for page in document:` loop instead of across the document.
- Failure/impact: Repeated images (such as logos, watermarks, or headers present on every page) are re-extracted on every page. In multi-page documents, this bloats output with hundreds of redundant base64 data blocks.
- Config / remediation: Lift `seen` set initialization outside the page loop.
- Source: `scripts/docmd:886-893`
- Default check: Line 888 creates a new `seen = set()` for every page iteration.
- Confidence: High

### Finding 12: Corrupt Inner Streams / XML Return Exit Code 1 Instead of 2
- Current: `scripts/docmd:1121-1126`, `scripts/docmd:1144-1146`
- Gap: `convert_source` maps exceptions to exit codes via `exit_code_for(exc)`. Only `CorruptDocumentError` yields exit code 2. Only initial opening in `open_office_source` and `open_pdf` wraps exceptions in `CorruptDocumentError`. Internal corruption (such as malformed XML inside DOCX/PPTX or corrupted MuPDF streams) raises `XMLSyntaxError`, `KeyError`, or `RuntimeError`.
- Failure/impact: `exit_code_for` returns exit code 1 (CLI failure) instead of exit code 2 (corrupt document), violating the documented contract for corrupt inputs.
- Config / remediation: Wrap internal parsing errors in `CorruptDocumentError`.
- Source: `scripts/docmd:1121-1126`, `scripts/docmd:1144-1146`
- Default check: Tested zip container with malformed `word/document.xml`; raised `XMLSyntaxError` resulting in exit code 1 instead of 2.
- Confidence: High

## Failure modes
- Process Hang (DoS): Cyclic `w:basedOn` style inheritance in DOCX causes an infinite loop in `style_size` and `is_bold` at 100% CPU.
- Runtime Crashes: Missing `Heading 1`..`Heading 6` or `Normal` styles, missing notes placeholders, or unresolvable image relationships raise unhandled exceptions.
- Silent Content Loss: Grouped PPTX shapes are skipped, nested tables in DOCX are ignored.
- Output Corruption: Spanning headers in multi-column PDFs cause columns to interleave horizontally.
- Redundant Output: Page-scoped image deduplication extracts shared headers/logos repeatedly.
- Exit Code Inversion: Corrupt inner streams exit 1 instead of 2.

## Seams
- Decryption Seam: `open_office_source` decrypts encrypted Office files via `msoffcrypto` into `BytesIO`.
- Image Extraction Seam: Document converters emit inline base64 data URIs.
- PDF Layout Seam: `extract_pdf_lines` extracts spans and lines, calls `order_pdf_lines`, and runs `strip_pdf_margins`.
- OCR Fallback Seam: When digital text on a PDF page falls below 50 characters, `ocr_pdf_page` triggers via RapidOCR.
- OCR Deduplication Seam: `pdf_image_blocks` hashes extracted image bytes using SHA-256 and caches OCR text in `ocr_cache`.

## Rejected defaults
- Assuming English Style Names in DOCX: Relying on "Heading 1" through "Heading 6" and "Normal".
- Flat Shape Iteration in PPTX: Assuming slide content is only present at top-level `slide.shapes`.
- Page-Level PDF Image Deduplication: Resetting `seen` image XREFs per page.
- Font-Size-Only Paragraph Splitting in PDF: Only splitting paragraphs when heading font sizes change or page breaks occur.

## Open Questions
None.
