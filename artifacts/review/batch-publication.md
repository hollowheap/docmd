# Robustness Review: Batch Publication (V06)

Scope: `convert_directory` staging and commit walk, `scripts/docmd:2678-2770`. Outcome: a failed batch publishes exactly the documents that sort before the first failure.

## Lens ledger

| Lens | Status | Reason |
|---|---|---|
| backend | considered | No transport, schema, retry, or pool-lifecycle change. |
| security | considered | No new trust boundary. Staging stays under `-o`. |
| performance | loaded | Commit walk is O(n). Later documents convert after the first failure; not measured. |
| ui | considered | No rendered output. |
| simplicity | loaded | No new helper, option, or abstraction. |

## Findings

### Finding 1: Unguarded OSError in the commit walk (fixed)
- Current: `scripts/docmd:2764` (`commit_staged_output`)
- Gap: `convert_one` guards its writes with `except OSError`. The commit walk did not.
- Failure/impact: A commit error prints a traceback. The failing document can end half-committed: `commit_staged_output` moves assets (`scripts/docmd:2668`) before it replaces the Markdown (`scripts/docmd:2675`).
- Reproduction: `mkdir -p out/b.md` with a three-document batch whose documents contain images. The run printed `IsADirectoryError` and left `out/b.assets` without a valid `out/b.md`.
- Fix: catch `OSError`, print `docmd: error: cannot write <final>: <exc>`, return exit code 1, and stop the walk. The exit code stays 1.
- Not fixed: the assets-before-Markdown order. A full fix needs an atomic directory swap. That is a larger change with no current requirement.
- Confidence: High (reproduced).

## Failure modes
- Verification failure: the staged files are never moved and the staging directory is removed. Covered by `test_verify_failure_publishes_only_earlier_documents`.
- Worker exception: `future.result()` raises before the commit walk. Nothing is published. The `finally` block removes staging (`scripts/docmd:2769-2770`).
- Ordering: the walk reads `results` in sorted document order, so the output is the same at any `--jobs` value.
- Stale output: a rerun does not delete outputs that earlier runs wrote. Reproduced: after a verify failure on `b`, the old `out/b.md` and `out/c.md` remain. See `Q03`.
- Staging after SIGKILL: a killed process leaves `.docmd-stage-*` in `-o`. `discover_documents` ignores dot-prefixed paths. UNVERIFIED by kill test.
- Link verification: verify runs against the staging directory, so a link to a sibling output file would not resolve there. The converters emit only data URIs and external links. UNVERIFIED.

## Seams
- Staging seam: `staged_path` maps each document into the private staging directory.
- Commit seam: `commit_staged_output` moves assets and Markdown into `-o`.
- Status seam: `results[document]` holds the staged path and status for the commit walk.

## Rejected defaults
- Cancel pending futures after the first failure: the commit walk needs earlier documents' results, and no measurement shows a cost.
- Stop converting at the first failure with `--jobs 1`: this hides later error messages on stderr.

## Open Questions
- Q03 in `artifacts/questions.md`.
