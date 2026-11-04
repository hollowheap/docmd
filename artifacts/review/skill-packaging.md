# Robustness Review: Skill Packaging (V05)

## Findings

### Finding 1: Omission of `metadata.version` from Required Frontmatter Validation
- Current: `scripts/dist.py:34`, `scripts/dist.py:68-70`
- Gap: `REQUIRED_FRONTMATTER = ("name", "description", "license", "compatibility")` lacks `"metadata.version"`, despite AGENTS.md explicitly stipulating that `SKILL.md` frontmatter must keep `name`, `description`, `license`, `compatibility`, and `metadata.version`.
- Failure/impact: Incomplete `SKILL.md` missing `metadata.version` passes `dist.py` build and smoke tests without failure, producing an invalid skill manifest for `skills.sh`.
- Config / remediation: Include `"metadata.version"` in `REQUIRED_FRONTMATTER`.
- Source: `scripts/dist.py:34`, `AGENTS.md:29`
- Default check: Removing `metadata.version` from `SKILL.md` currently exits 0 in `dist.py`.
- Confidence: High

### Finding 2: Lack of PEP 723 Dependency Parity and `opencv-python-headless` Verification in `dist.py`
- Current: `scripts/dist.py:28-33`, `scripts/dist.py:63-65`
- Gap: `PEP723_MARKERS` only checks for raw substrings. `dist.py` never asserts dependency parity against `pyproject.toml`, nor does it verify the presence of `opencv-python-headless`.
- Failure/impact: If dependencies drift between `pyproject.toml` and `scripts/docmd`, or if `opencv-python-headless` is replaced by GUI `opencv-python`, `dist.py` succeeds without error, failing only in headless environments.
- Config / remediation: Parse the PEP 723 block and assert parity with `pyproject.toml`.
- Source: `scripts/dist.py:28-33`, `tests/test_packaging.py:21-39`, `AGENTS.md:24-25`
- Default check: Removing a dependency from `scripts/docmd` still passes `dist.py`.
- Confidence: High

### Finding 3: Non-Atomic File Replacement in `dist.py:build()`
- Current: `scripts/dist.py:76-78`
- Gap: `shutil.copyfile(SOURCE, PACKAGED)` directly opens and truncates `skills/docmd/scripts/docmd`, followed by `PACKAGED.chmod(0o755)`.
- Failure/impact: If the build process is terminated midway, `skills/docmd/scripts/docmd` is left in a truncated, corrupt, or non-executable state.
- Config / remediation: Write to a temporary file in the destination directory and atomically rename using `os.replace`.
- Source: `scripts/dist.py:76-78`
- Default check: Truncation on interrupted copy leaves corrupt destination file.
- Confidence: High

### Finding 4: Premature Packaging Promotion Prior to Smoke Test Validation
- Current: `scripts/dist.py:114-117`
- Gap: `main()` runs `build()` followed by `smoke()`. `build()` mutates `skills/docmd/scripts/docmd` before testing whether conversions run.
- Failure/impact: If changes contain runtime syntax errors or conversion regressions, the publishable tree is overwritten with broken artifacts despite a failed build command.
- Config / remediation: Stage the script to a temporary executable path, run `smoke()` against it, and promote only on success.
- Source: `scripts/dist.py:114-117`
- Default check: Runtime syntax error leaves `skills/docmd/scripts/docmd` broken after failed smoke run.
- Confidence: High

### Finding 5: Smoke Conversions Omit `--verify` Validation
- Current: `scripts/dist.py:91-104`
- Gap: `smoke()` runs conversion without the `--verify` flag.
- Failure/impact: `smoke()` only asserts non-empty output and asset creation. Regressions resulting in broken GFM table columns, unbalanced code fences, or unresolvable assets are not caught by smoke tests.
- Config / remediation: Pass `--verify` to smoke test conversions.
- Source: `scripts/dist.py:91-104`, `AGENTS.md:32`
- Default check: Broken tables or fences in fixtures pass smoke tests without `--verify`.
- Confidence: High

### Finding 6: Triplicate Version Declarations Lack Parity Check
- Current: `pyproject.toml:3`, `scripts/docmd:31`, `skills/docmd/SKILL.md:9`
- Gap: Version `"0.2.1"` is declared independently in three locations (`pyproject.toml`, `scripts/docmd`, `SKILL.md`). Neither `dist.py` nor test suites enforce that all three match.
- Failure/impact: Bumping the version in one file leaves mismatched metadata published to skill indexers.
- Config / remediation: Assert version parity in `dist.py` build validation.
- Source: `pyproject.toml:3`, `scripts/docmd:31`, `skills/docmd/SKILL.md:9`
- Default check: Version mismatch passes `dist.py`.
- Confidence: High

### Finding 7: Unhandled Missing Executable Exception for `uv` in `smoke()`
- Current: `scripts/dist.py:91-104`
- Gap: `subprocess.run(["uv", ...])` is called without checking `shutil.which("uv")` or catching `FileNotFoundError`.
- Failure/impact: In environments without `uv`, running `dist.py` fails with a raw Python traceback rather than an informative error message.
- Config / remediation: Check `shutil.which("uv")` before running smoke conversions.
- Source: `scripts/dist.py:91-104`
- Default check: `PATH="" python3 scripts/dist.py` crashes with uncaught `FileNotFoundError`.
- Confidence: High

### Finding 8: `frontmatter_fields()` Parser Fails on CRLF Line Endings
- Current: `scripts/dist.py:37-41`
- Gap: `if not text.startswith("---\n"): return fields` assumes strictly LF line terminators.
- Failure/impact: If `SKILL.md` is checked out with `\r\n` (CRLF), `frontmatter_fields()` returns an empty dict, causing a false positive build error.
- Config / remediation: Normalize newlines with `text = text.replace("\r\n", "\n")` before parsing.
- Source: `scripts/dist.py:37-41`
- Default check: CRLF-formatted `SKILL.md` returns empty fields dictionary.
- Confidence: High

## Failure modes
- Headless Environment Import Failure: Missing `opencv-python-headless` passes smoke tests without OCR, failing in production containers.
- Broken Publishable Tree on Build Abort: Corrupt script promoted before smoke tests succeed.
- Dirty Git State: Interrupted copy operations truncate packaged executable.
- Undetected Markdown Degradation: Smoke tests without `--verify` overlook table or asset defects.
- Cross-Platform CRLF Failure: CRLF line endings break frontmatter extraction.

## Seams
- Single Source of Truth Seam: `scripts/docmd` syncs into `skills/docmd/scripts/docmd`.
- Packaging Manifest Seam: `pyproject.toml`, PEP 723 inline script header, and `SKILL.md` frontmatter share contract.
- Fixture Conversion Seam: `sample.{docx,pptx,pdf}` smoke-converted into isolated temporary directories.
- Asset Extraction Seam: Smoke tests verify asset directory extraction.

## Rejected defaults
- Enabling OCR in Smoke Tests: Rejected to avoid long model loading and inference latency on routine builds.
- External Packaging Frameworks: Standalone PEP 723 script with `uv` preferred over complex wheel builds.
- In-Repo Smoke Output: Temporary directories in system `/tmp` prevent dirty git working copy.

## Open Questions
None.
