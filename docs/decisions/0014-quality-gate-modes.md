# ADR 0014 — Quality gate modes: advisory, strict-required, hacs-publish, upgrade-radar

- **Status**: Accepted
- **Date**: 2026-05-02
- **Tag**: v0.14.x (#148)

## Context

`hasscheck check` has historically exited non-zero when any finding carries
`status=fail`. This binary behavior is fine for a first iteration but becomes
friction in three real use-cases:

1. **Informational dashboards** — a team wants to embed HassCheck in CI and
   see signals in the report without ever blocking a merge. They need a mode
   where the check always exits 0 regardless of findings.

2. **HACS submission gates** — HACS evaluates both REQUIRED and RECOMMENDED
   findings when deciding whether to accept an integration. A CI gate that
   only blocks on FAIL misses WARN-level signals; a gate that blocks on any
   FAIL or WARN on any severity is too strict for non-publishing workflows.

3. **Upgrade Radar pipeline** — the hub's per-HA-version pipeline needs to
   flag regressions in `version.*` rules without blocking unrelated manifest or
   branding rule work.

The schema_version bump to 0.6.0 provides the right moment to introduce a
structured `gate:` stanza so users can declare their exit-code policy
declaratively rather than wrapping the CLI in shell logic.

## Decision

### 1. Gate trigger predicate: `status in {FAIL, WARN}` for named modes

All four named gate modes share the same trigger threshold: a finding is
"triggered" when its `status` is either `fail` or `warn`. This is deliberate —
a `warn` in a required rule is still a signal that the gate author cares about,
and treating `warn` as safe would silently hide regressions. The legacy path
(no `gate:` stanza) preserves the pre-0.6.0 behavior: only `fail` triggers a
non-zero exit.

### 2. `hacs-publish` ships covering REQUIRED + RECOMMENDED (HACS tags follow-up)

The HACS review rubric covers both REQUIRED and RECOMMENDED severity rules.
`hacs-publish` therefore blocks on any finding in those two severity tiers that
is `fail` or `warn`. A follow-up issue (`TODO(hacs-tags)`) will refine this
once rules carry explicit `tags=("hacs",)` metadata, allowing the gate to
target only rules that HACS actually evaluates rather than the whole RECOMMENDED
tier. Until that metadata exists, REQUIRED + RECOMMENDED is the correct
conservative approximation.

### 3. `custom` mode deferred — not in the enum

The design considered a `custom` mode (user-supplied predicate). This was
deferred because it requires either a DSL, a Python callout, or a tag-filter
syntax — none of which are ready. The four named modes cover all identified
use-cases at launch. `custom` will follow as a separate ADR when tags land.

### 4. Absent `gate:` stanza = legacy FAIL-only behavior preserved

A `hasscheck.yaml` without a `gate:` key (including all pre-0.6.0 configs)
continues to exit non-zero only on `fail` findings. This is the zero-migration
path: existing configs do not need to be updated to get the old behavior.
`gate: null` is equivalent to omitting `gate:` entirely.

### 5. `gate_mode` in JSON output deferred

The JSON report does not yet include the active gate mode or the gate decision.
Adding it requires a schema bump decision (what field, what shape, whether it
belongs under `summary` or `validity`). Deferred to a follow-up issue. The
current report shape is stable at schema 0.5.0; the `gate:` stanza is a
CLI-only exit-code policy and does not affect the report payload.

## Consequences

- **schema_version 0.6.0 is introduced.** All existing versions (0.2.0–0.5.0)
  remain valid. The `gate:` field is rejected on any schema version below 0.6.0
  with a clear validation error.
- **`hasscheck init` and the scaffold template** produce `schema_version: "0.6.0"`
  as the new default. Existing `hasscheck.yaml` files at lower versions continue
  to parse without modification.
- **Four gate modes are frozen.** Adding a fifth mode requires a follow-up ADR
  and a `GateMode` enum member. Removing a mode is a breaking change.
- **`should_exit_nonzero` is a pure function.** It takes findings and an
  optional `GateConfig` and is unit-testable without CLI setup. The CLI wires
  it in via a second `discover_config` call (intentional duplication for
  separation of concerns between report production and exit-code policy).
- **No `case _` in the match statement** — a missing branch for a new enum
  member is a loud bug (Python raises `ValueError`) rather than a silent
  passthrough. This is intentional and documented in code.

## Alternatives considered

- **Single `strict` flag instead of named modes.** A boolean `strict: true`
  covering all severities was simpler but would not address the advisory
  (always-exit-0) or upgrade-radar (version-scoped) use-cases. Named modes
  are more expressive and self-documenting in CI configuration.

- **Shell-wrapping the exit code.** Teams could `|| true` or `|| exit 0` around
  the CLI invocation. Rejected: this hides the policy from the config file,
  makes it invisible to tooling, and duplicates the logic in every consuming
  repo. A declarative `gate:` stanza is a single source of truth.

- **Tag-based gate filter from the start.** A `gate: {tags: [hacs]}` syntax
  would be more composable than named modes. Rejected at launch: rules do not
  carry tags yet. Named modes are a stable interim solution that will remain
  valid after tags land (they will simply have more precise semantics).

- **Include `gate_mode` in the JSON report immediately.** Rejected: the gate
  decision is a CLI exit-code policy, not a quality signal. Adding it to the
  report before the schema field is designed would risk a breaking schema
  change. Deferred cleanly.

- **Block `warn` findings in legacy mode.** The pre-0.6.0 behavior exits
  non-zero only on `fail`. Changing that default would break every repo that
  currently runs without a `gate:` stanza and has `warn` findings. The legacy
  path is preserved exactly.

## Related

- ADR 0009 — Schema versioning policy (additive bump rule)
- ADR 0011 — Upgrade Radar status taxonomy
- ADR 0012 — Compatibility claim policy
- ADR 0013 — Integration version identity
- Issue #148 — This ADR's source issue
- TODO(hacs-tags) — Follow-up to add `tags=("hacs",)` to rule definitions
