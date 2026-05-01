# ADR 0004 — Project applicability context for v0.3

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.3 scope

## Context

v0.2 shipped `hasscheck.yaml` per-rule overrides:

```yaml
rules:
  repairs.file.exists:
    status: not_applicable
    reason: No user-fixable repair scenarios.
```

That solved the immediate warning-noise problem, but it creates honest friction:
maintainers must repeat per-rule overrides for common project-level facts.

ADR 0002 intentionally deferred Block A — project-level applicability flags — to
v0.3 because Block A is a rule-engine feature. A flag is only useful if concrete
rules consume it.

## Decision

v0.3 introduces a small `applicability:` block in `hasscheck.yaml` and wires it
to a limited set of rule consumers.

Initial flags:

```yaml
applicability:
  supports_diagnostics: false
  has_user_fixable_repairs: false
  uses_config_flow: false
```

Each flag is optional. Absence means "no declaration" and existing v0.2 behavior
continues.

## Scope

### In

- Extend `HassCheckConfig` with an optional `applicability` block.
- Add a `ProjectApplicability` Pydantic model with `extra="forbid"`.
- Route loaded config applicability into rule execution through context, not via
  global state.
- Add rule consumers:
  - `diagnostics.file.exists` consumes `supports_diagnostics`.
  - `repairs.file.exists` consumes `has_user_fixable_repairs`.
  - `config_flow.file.exists` consumes `uses_config_flow`.
  - `config_flow.manifest_flag_consistent` MAY use `uses_config_flow` only for
    no-signal cases; it MUST NOT hide file/manifest mismatches.
- Add JSON disclosure for config-driven applicability decisions.
- Add terminal disclosure when config applicability changed findings.
- Keep v0.2 per-rule overrides working unchanged.

### Out

- Static source-code auto-detection.
- Project flags from the original idea that no current rule consumes
  (`auth_required`, `has_devices`, `cloud_service`, `uses_config_entry`).
- Multi-integration support.
- Scaffolding commands.
- GitHub Action.

## Behavior rules

### 1. Flags only soften missing-signal warnings

A config applicability flag may convert a missing optional signal from `warn` to
`not_applicable`.

Example:

```yaml
applicability:
  has_user_fixable_repairs: false
```

If `repairs.py` is absent, `repairs.file.exists` becomes `not_applicable` with
`applicability.source = "config"`.

### 2. Natural PASS wins

If a file exists and the rule naturally passes, project applicability MUST NOT
turn it into `not_applicable`.

Example: if `diagnostics.py` exists but `supports_diagnostics: false`, the rule
still passes. This avoids stale config hiding real repository state.

### 3. Correctness failures remain locked

Applicability flags MUST NOT hide consistency or correctness failures.

Example: if `config_flow.py` exists but `manifest.json` does not set
`config_flow: true`, `config_flow.manifest_flag_consistent` still fails even when
`uses_config_flow: false`.

### 4. Per-rule overrides win over project applicability for non-PASS findings

Order:

1. Run rules with project applicability context.
2. Apply v0.2 per-rule overrides post-hoc.

This preserves v0.2's explicit override mechanism and keeps per-rule written
reasons as the strongest user intent.

### 5. Disclosure is mandatory

Config-driven applicability changes score denominators. They must be visible.

v0.3 adds a separate summary field rather than reusing `overrides_applied`:

```json
"applicability_applied": {
  "count": 2,
  "rule_ids": ["diagnostics.file.exists", "repairs.file.exists"],
  "flags": ["has_user_fixable_repairs", "supports_diagnostics"]
}
```

`overrides_applied` remains specific to v0.2 per-rule overrides.

## Schema/version policy

- Package/tool version becomes `0.3.0` when shipped.
- Report `schema_version` becomes `0.3.0` because `summary.applicability_applied`
  is a new JSON field.
- Existing v0.2 config files with only `rules:` must keep working.
- `hasscheck.yaml` with no `schema_version` is accepted and treated as current.
- Explicit `schema_version: "0.2.0"` is accepted for backward compatibility when
  using only v0.2 fields.
- Explicit `schema_version: "0.3.0"` is accepted for v0.3 fields.

## Rationale

- The initial flags are chosen from current rule pain, not from speculative
  product ideas. Flags with no consumers are dead config.
- Natural PASS wins because v0.2 already rejected PASS-to-N/A overrides as stale
  or suspicious. Project applicability should follow the same trust model.
- Correctness checks remain locked because HassCheck's credibility depends on not
  letting config hide broken wiring.
- A separate `applicability_applied` summary keeps JSON consumers from confusing
  project-level applicability with per-rule overrides.

## Alternatives rejected

### Add all idea.md flags now

Rejected. `auth_required`, `has_devices`, `cloud_service`, and
`uses_config_entry` are plausible future flags, but no current v0.3 rule has a
clear consumer. Adding them now would create dead config.

### Reuse `summary.overrides_applied`

Rejected. Per-rule overrides and project applicability are different sources of
user intent. Mixing them makes downstream badge/report logic harder to trust.

### Let flags override PASS findings

Rejected. This repeats the v0.2 S4.3 pitfall: stale config could hide files that
actually exist.

### Auto-detect applicability in v0.3

Rejected for initial v0.3 scope. Auto-detection is valuable, but should follow
explicit config consumers once behavior is proven.
