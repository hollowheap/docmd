# Architectural Exploration: Document Conversion Seams and Packaging

## Destination
A zero-install CLI and publishable skill that converts DOCX, PPTX, and PDF documents into GitHub Flavored Markdown with offline OCR and verified local assets.

## References
- `AGENTS.md`
- `artifacts/context.md`
- `scripts/docmd`

## Archetypes
- Archetype 1: Monolithic Single-File CLI with Bundled Distribution
  - Structure: `scripts/docmd` as source of truth, `skills/docmd/scripts/docmd` synced via `scripts/dist.py`.
- Archetype 2: Multi-Package Python Distribution with Wheel Publishing
  - Structure: `src/docmd/`, `pyproject.toml`, PyPI releases, external package registry.

## Trade-offs
- Coupling: Archetype 1 (Low) vs Archetype 2 (High)
- Blast radius: Archetype 1 (Isolated) vs Archetype 2 (Broad)
- YAGNI: Archetype 1 (Clean) vs Archetype 2 (Premature)
- Failure mode: Archetype 1 (file drift caught by dist.py smoke tests) vs Archetype 2 (version desync across registry, lockfile, and skill manifests)

## Recommendation
Archetype 1 fits repository conventions: PEP 723 execution with `uv` enables zero-install usage for agents, while `scripts/dist.py` provides deterministic validation for the `skills/docmd` tree.

## Open Questions
See `artifacts/questions.md#brainstorm-conversion-seams`. Do not duplicate question entries here.

## Out of scope
- Multi-format document editor or round-trip Markdown to Office exporter.
- Cloud OCR services or external binary daemons.
