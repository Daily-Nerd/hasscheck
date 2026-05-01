# ADR 0009 — Schema versioning policy: SCHEMA_VERSION bump cadence and lockstep

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.8 hygiene

## Context

`src/hasscheck/models.py:11` defines `SCHEMA_VERSION = "0.3.0"`. This constant is
embedded in every JSON report emitted by `hasscheck check --format json` and is
the primary contract signal between the CLI and any downstream consumer (hosted
service, CI tooling, stored reports).

ADR 0008 (hosted reports publish contract) established a strict version-match
lockstep between `hasscheck` (CLI/OSS) and `hasscheck-web` (hosted server). The
server rejects payloads whose `schema_version` does not match its built-against
version with HTTP 422 (`error: "schema_version_mismatch"`). This makes the
schema version a hard coordination point across two repositories.

ADR 0006 (ruleset versioning) governs `DEFAULT_RULESET_ID` and
`DEFAULT_SOURCE_CHECKED_AT`. These are **separate version axes** from
`SCHEMA_VERSION` and do not trigger schema bumps. Adding a new rule changes the
ruleset ID, not the schema version.

Without a documented policy, contributors face two failure modes:

1. **Over-bumping**: bumping `SCHEMA_VERSION` on every PR that touches
   `models.py`, even for non-shape-changing refactors. This corrupts the strict
   lockstep contract and creates unnecessary cross-repo coordination churn.
2. **Under-bumping**: never bumping it, silently breaking the server's
   strict-match contract when fields actually change.

Both outcomes are unsafe for a hosted service already in production. This ADR
is policy-only; it does not bump `SCHEMA_VERSION` (stays `"0.3.0"` for v0.8 —
no Finding-shape changes landed in this cycle).

## Decision

### Format

`SCHEMA_VERSION` is a semver string `"X.Y.Z"`, identical in form to the
project's tool version, but **independent of it**. Tool version `0.7.0` and
schema version `0.3.0` are decoupled and advance on separate cadences.

Current value: `"0.3.0"` (set in `src/hasscheck/models.py:11`).

### Bump triggers (when to bump)

A `SCHEMA_VERSION` bump is **required** when any of the following changes ship:

1. A new field is added to `HassCheckReport`, `Finding`, `RulesetInfo`,
   `ProjectInfo`, `ToolInfo`, `CategorySummary`, `OverridesApplied`,
   `ApplicabilityApplied`, or any model serialized into the JSON report.
2. An existing field's type changes (e.g. `str` → `list[str]`, `bool` → `str`).
3. An existing field is renamed.
4. An existing field is removed.
5. An enum value is added, removed, or renamed (e.g. a new `RuleStatus`, a new
   `ApplicabilityStatus`).
6. The semantic meaning of an existing field changes (e.g. `repo_slug`
   redefined from "git remote derived" to "manifest-derived only").

Versioning rule:

- **MAJOR** bump (`X.0.0`): breaking change — field removed, renamed, type
  changed in a non-backward-compatible way, or semantic meaning altered.
- **MINOR** bump (`x.Y.0`): additive — new optional field, new enum value, new
  model added.
- **PATCH** bump (`x.y.Z`): reserved for clarification-only changes (typos in
  field descriptions in JSON schema output); should be rare.

### Lockstep with `hasscheck-web` (per ADR 0008)

The hosted service validates incoming payloads against one specific
`SCHEMA_VERSION`. Mismatch → HTTP 422 with `error: "schema_version_mismatch"`.

Any PR that bumps `SCHEMA_VERSION` **must** be coordinated with a corresponding
`hasscheck-web` deploy that bumps the server's accepted version in the same
release window.

Coordination checklist (include in the PR description):

1. Confirm the equivalent `hasscheck-web` PR exists and is ready to deploy.
2. Confirm test fixtures in **both** repos use the new `SCHEMA_VERSION`.
3. Confirm the server-side `expected` field in 422 error responses references
   the new version.
4. Document the bump and lockstep coordination in `CHANGELOG.md`.

Note: `tests/test_publish.py` lines 108, 122, and 128 currently hardcode
`"0.3.0"`. These **must** be updated on every schema bump and are part of the
bump checklist.

### Additive-only stance (preferred)

The project explicitly prefers MINOR (additive) bumps over MAJOR (breaking)
bumps. Removals and renames break server lockstep coordination and break any
maintainer-stored historical reports.

A removal **should** be staged: deprecate first (still emit but mark as
deprecated in JSON schema docstrings, bump MINOR); remove in a later cycle
(bump MAJOR).

ADR 0006 already states "additive-only" for the ruleset surface. This ADR
extends the stance to the schema surface.

## What does NOT trigger a bump

These changes **must not** bump `SCHEMA_VERSION`:

- Adding a new rule (changes `DEFAULT_RULESET_ID` per ADR 0006, not
  `SCHEMA_VERSION`).
- Updating `DEFAULT_SOURCE_CHECKED_AT` (ruleset freshness, ADR 0006 territory).
- Refactoring `models.py`, `checker.py`, `output.py`, or any non-rule,
  non-schema module when the JSON output shape is unchanged.
- Changing rule logic (e.g. fixing a regex in a checker) when the JSON output
  shape is unchanged.
- Adding or modifying CLI commands that do not change the JSON report shape
  (e.g. `hasscheck explain`, `hasscheck init`).
- Adding tests, docs, or ADRs.
- Reformatting or linting.

## Consequences

### Positive

- Server (`hasscheck-web`) and clients (`hasscheck` CLI) stay in lockstep with
  no silent drift.
- Maintainers reading historical `schema_version` in stored reports can reason
  about backward compatibility.
- Contributors get a clear, enumerable checklist of what does and does not
  trigger a bump.
- The distinction from ADR 0006 (ruleset versioning) prevents accidental
  conflation of two separate version axes.

### Negative

- Requires contributor discipline; reviewers must check every `models.py` PR
  against this policy.
- Lockstep with `hasscheck-web` adds cross-repo coordination cost. Mitigated by
  the coordination checklist above.
- Hardcoded `"0.3.0"` in `tests/test_publish.py` will need updates on every
  bump. This is in scope for that bump's PR; it is out of scope for v0.8.

## Alternatives considered

- **Reuse `project.version` as `SCHEMA_VERSION`** — rejected: tool releases
  bump for many reasons unrelated to schema (CLI features, action inputs,
  performance). Conflating them would force schema-version bumps on every
  release and corrupt the lockstep contract.
- **No formal versioning; "the schema is whatever the latest CLI emits"** —
  rejected: makes server-side validation impossible; ADR 0008's strict-match
  contract requires a stable, explicit version.
- **Permissive server validation (accept any `schema_version` >= server's)** —
  rejected: defers the lockstep problem rather than solving it; ADR 0008
  explicitly chose strict match. Permissive validation is deferred until
  multiple live schemas are supported (post-v1.0 work).

## References

- ADR 0006 — Ruleset versioning (`DEFAULT_RULESET_ID`, `DEFAULT_SOURCE_CHECKED_AT`) — distinct from schema version
- ADR 0008 — Hosted reports publish contract (strict version-match lockstep)
- `src/hasscheck/models.py:11` — `SCHEMA_VERSION` constant location
- `tests/test_publish.py` lines 108, 122, 128 — hardcoded version strings to update on every bump
- GitHub Issue #15 — PyPI publish (when this lands, revisit `Development Status :: 3 - Alpha` classifier)
