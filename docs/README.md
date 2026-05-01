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

| Version | Status | Tag | Theme |
|---|---|---|---|
| v0.1.0 | Shipped | `v0.1.0` | Local CLI, JSON contract, initial rule set |
| v0.2.0 | Shipped | `v0.2.0` | `hasscheck.yaml` per-rule overrides |
| v0.2.1 | Shipped | `v0.2.1` | Maintenance |
| v0.3.0 | Shipped | `v0.3.0` | Project applicability context |
| v0.4.0 | Shipped | `v0.4.0` | Scaffolding helpers + fix rendering |
| v0.5.0 | Shipped | `v0.5.0` | Composite GitHub Action + markdown report |
| v0.6.0 | Shipped | `v0.6.0` | Opt-in shields.io badge generator |
| v0.7.0 | In planning | — | Opt-in hosted reports (separate `hasscheck-web` private service) |

## Architecture docs

- [`architecture/config-file.md`](./architecture/config-file.md) — `hasscheck.yaml` shape and override merging
- [`architecture/project-applicability-context.md`](./architecture/project-applicability-context.md) — `applicability:` block design
- [`architecture/scaffolding.md`](./architecture/scaffolding.md) — Scaffolding engine and templates
- [`architecture/badges.md`](./architecture/badges.md) — Badge generator + GitHub Pages recipe
- [`architecture/publish-handshake.md`](./architecture/publish-handshake.md) — v0.7 publish client (OIDC, request/response, error semantics)

## Decision records

- [ADR 0001 — Config override policy](./decisions/0001-config-override-policy.md)
- [ADR 0002 — Block A deferred to v0.3](./decisions/0002-block-a-deferred-to-v03.md)
- [ADR 0003 — `hasscheck.yaml` config-file override policy](./decisions/0003-config-file-override-policy.md)
- [ADR 0004 — Project applicability context for v0.3](./decisions/0004-project-applicability-context.md)
- [ADR 0005 — Scaffolding policy for v0.4](./decisions/0005-scaffolding-policy.md)
- [ADR 0006 — Ruleset versioning policy](./decisions/0006-ruleset-versioning.md)
- [ADR 0007 — Badge policy: opt-in only, forbidden language, layered status](./decisions/0007-badge-policy.md)
- [ADR 0008 — Hosted reports publish contract](./decisions/0008-hosted-reports-publish-contract.md)

## A note on v0.7 and the OSS/proprietary split

v0.7 introduces an opt-in hosted reports service. The hosted service ships
as a sibling **private** repository, `hasscheck-web`, not as part of this
OSS repository. This repository continues to ship the CLI, GitHub Action,
rules, scaffolds, and badge generator that maintainers run locally or in
their own CI. ADR 0008 documents the contract between the two repos.

The free local-CLI / GitHub-Action / committed-badge-JSON path remains
fully functional and is permanent; v0.7's hosted service is purely additive
and opt-in.
