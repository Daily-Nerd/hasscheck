# HassCheck Documentation

Living documentation for HassCheck. The original product brief lives in
[`../idea.md`](../idea.md) and is preserved as the founding vision —
look here for the current state of the project, architecture decisions,
and per-feature design.

## Structure

- [`architecture/`](./architecture/) — How current and upcoming features
  work. Updated as the codebase evolves.
- [`decisions/`](./decisions/) — Architecture Decision Records (ADRs).
  Numbered, dated, immutable once accepted. Override an ADR by writing
  a new one that supersedes it; do not rewrite history.

## Project status

| Version | Status | Branch / tag | Notes |
|---|---|---|---|
| v0.1.0 | Shipped | `v0.1.0` (`56b9cc5`) | Local CLI, JSON contract, 23 rules across 7 categories, fixture-based tests. |
| v0.2.0 | In progress | `feature/config-file-support` | Adds `hasscheck.yaml` for per-rule applicability overrides. |

## v0.2 entry points

- Architecture: [`architecture/config-file.md`](./architecture/config-file.md)
- Decisions:
  - [ADR 0001 — Config override policy](./decisions/0001-config-override-policy.md)
  - [ADR 0002 — Block A deferred to v0.3](./decisions/0002-block-a-deferred-to-v03.md)
