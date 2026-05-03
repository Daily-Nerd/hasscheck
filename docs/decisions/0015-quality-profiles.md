# ADR 0015 — Quality profiles: cloud-service, local-device, hub, helper, read-only-sensor, core-submission-candidate

- **Status**: Accepted
- **Date**: 2026-05-02
- **Tag**: v0.15.x (#146)

## Context

Different Home Assistant integration shapes (cloud-backed services, LAN-only
devices, hubs/coordinators, helper integrations, read-only sensors,
core-submission candidates) have meaningfully different quality expectations.
A single uniform RECOMMENDED baseline either over-warns one shape (e.g. asking
local-device integrations for a privacy policy) or under-warns another (e.g.
not boosting reauth for cloud services). Per-rule overrides exist but require
authors to know each rule individually — high friction. Profiles let authors
pick a curated baseline in one line.

## Decision

### 1. Profile definitions live as frozen Python dataclasses (not YAML)

Profiles are frozen Python dataclasses (`ProfileDefinition`) defined in
`src/hasscheck/profiles.py`. This is type-safe, fast to import, trivially
testable, and requires no file I/O. User-defined profile YAML files are
deferred post-v1.

### 2. New `profile: str | None` field on HassCheckConfig (schema 0.7.0)

The `profile` field is added to `HassCheckConfig` gated behind
`schema_version: "0.7.0"`. The validator pattern matches ADR 0014 (#148):
older schema versions reject the field with a clear `ValidationError`. Profile
name validation is deferred to `run_check` (not Pydantic) to avoid coupling
the config layer to the profile registry.

### 3. `--profile <name>` CLI flag on `check` command

The `check` command gains an optional `--profile <name>` flag. Omitting it
leaves `profile=None` and preserves pre-0.15.0 behavior exactly.

### 4. Apply order: profile severity/disables FIRST, then per-rule RuleOverride

Override order in `run_check`:
1. Rules fire → raw findings.
2. `apply_profile_overrides` applies profile severity boosts and disables.
3. `apply_overrides` applies per-rule `RuleOverride` entries from
   `hasscheck.yaml` — user intent always wins over profile.

This ensures profiles are curated recommendations, not mandates. A user can
always silence a rule that the profile boosted to REQUIRED.

### 5. CLI `--profile` wins over `profile:` in hasscheck.yaml

When both the CLI `--profile` flag and `profile:` in `hasscheck.yaml` are
present, the CLI value takes precedence. This matches `--no-config` precedence
semantics: the most-recent explicit intent wins.

### 6. Non-overridable rules are silently skipped by profiles

Profiles cannot mutate rules with `overridable=False`. Any rule_id from
`profile.severity_overrides` or `profile.disabled_rules` whose rule has
`overridable=False` is silently passed through unchanged at apply time. This
keeps locked rules truly locked — profiles are recommendations, not bypasses.

### 7. RuleDefinition.profiles stays empty in v1; PROFILES owns the mapping

The `RuleDefinition.profiles` field (issue #147) is intentionally left empty
in v1. The `PROFILES` mapping in `src/hasscheck/profiles.py` is the single
source of truth for which profiles a rule belongs to. This avoids churn across
52+ rule definitions when adjusting profiles. A future `RuleDefinition.profiles`
backfill can be done as a separate, mechanical PR once the profile set
stabilises.

## Consequences

- **schema_version bumps 0.6.0 → 0.7.0.** Older configs (0.2.0–0.6.0) still
  parse; the `profile` field is rejected on versions below 0.7.0 with a clear
  validation error.
- **`ApplicabilitySource` Literal extends to include `"profile"`.** This is
  schema-visible (findings JSON `applicability.source`) but additive; existing
  consumers that read this field treat it as opaque text and continue to work.
- **`hasscheck init` and the scaffold template** produce
  `schema_version: "0.7.0"` as the new default. Existing `hasscheck.yaml`
  files at lower versions continue to parse without modification.
- **`core-submission-candidate` is intentionally aggressive** (~43 boosts —
  every overridable RECOMMENDED rule). Authors should only use this profile
  when actively preparing for upstream Core contribution.
- **A parity test** (`test_core_submission_candidate_covers_every_overridable_recommended_rule`)
  enforces that `_CORE_SUBMISSION_RULE_IDS` in `profiles.py` stays in sync with
  the rule registry. When a new overridable RECOMMENDED rule lands, the test
  fails, forcing the author to decide whether it belongs in core-submission.
- **A future `--profile auto`** (shape detection) is non-breaking — the design
  leaves room for it without schema changes.

## Alternatives considered

- **YAML profile files at v1** — deferred; adds I/O and parser surface for no
  v1 benefit. Python dataclasses are simpler and more testable.

- **Backfill `RuleDefinition.profiles` on all 52 rules** — rejected per D7;
  the profile→rule mapping lives in `profiles.py` to avoid per-rule churn.

- **Profile wins over per-rule `RuleOverride`** — rejected; user explicit
  intent must always win.

- **Profile name validated at Pydantic load time** — rejected; would couple
  the config layer to the profile registry and require importing `profiles.py`
  from `config.py`. Validation deferred to `run_check` is cleaner.

- **Empty `--profile ""` raising a `BadParameter`** — rejected; short-circuits
  naturally to the config value or `None` via `profile or ...`. Acceptable
  behavior.

- **`core-submission-candidate` derived from registry at import time** —
  rejected; silent semantics drift when adding new RECOMMENDED rules. The
  explicit literal list plus the parity test is intentional.

## Related

- ADR 0014 — Quality gate modes (parallel feature; gate is independent of profile)
- Issue #146 — Source issue
- Issue #147 — Added `RuleDefinition.profiles` field (now intentionally unused in v1)
- Proposal: `sdd/146-quality-profiles/proposal` (engram)
