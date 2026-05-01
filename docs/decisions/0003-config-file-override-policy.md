# ADR 0003 — hasscheck.yaml config-file override policy (v0.2)

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.2 implementation

## Context

v0.2 ships `hasscheck.yaml` per-rule applicability overrides. Several cross-cutting decisions
were needed before the spec phase was locked.

## Decisions

### Q1 — Config file name: `hasscheck.yaml` (exact, at repo root)

No `.hasscheck.yaml`, no `pyproject.toml` embedding, no parent-dir walk.
Discovery is `path / "hasscheck.yaml"` exact lookup only.

**Rationale**: single unambiguous location; mirrors common tool conventions (`.eslintrc`,
`pyrightconfig.json`). Parent-dir walk would silently inherit configs across projects.

### Q3 — Unknown top-level keys → `extra="forbid"` (ValidationError)

`HassCheckConfig` uses `model_config = ConfigDict(extra="forbid")`. Unknown keys
(e.g. Block A's `applicability:` deferred to v0.3) raise a `ConfigError` immediately.

**Rationale**: graceful upgrade path is opt-in; a corrupt config must not run silently.

### Q8 — Natural NOT_APPLICABLE + user override → silent no-op

When a rule naturally returns `NOT_APPLICABLE` (e.g. no integration detected), a user
override targeting that rule is silently ignored. Source stays `"default"`, count stays 0.

**Rationale**: the rule already resolved in the user's favour; the override is redundant.
A warning here would be noise on every run for repos that don't have the relevant files.

### Q10 — Mixed-status rules: `hacs.file.parseable` and `config_flow.manifest_flag_consistent` locked

Both rules are `overridable=False` despite being `severity=RECOMMENDED`.

- `hacs.file.parseable`: softening hides JSON corruption — correctness, not preference.
- `config_flow.manifest_flag_consistent`: consistency check; softening masks broken wiring.

**Rationale**: `overridable` is about whether the rule outcome can legitimately vary by
project intent, not about severity. These two can only be wrong, never "not applicable".

### Q-A — Terminal banner when `overrides_applied.count > 0`

`print_terminal_report` emits `"N override(s) applied from hasscheck.yaml."` before the
findings table whenever at least one override was applied.

**Rationale**: overrides change the apparent health of the report; users and reviewers must
know the report was produced with a config file. Banner is pre-table so it's never missed.

### Q-B — `RuleDefinition.overridable` carries no default

The `overridable: bool` field on the frozen dataclass has no default. Every rule definition
must explicitly declare it; omission causes a `TypeError` at import time.

**Rationale**: audit enforcement at the type level. A new rule cannot slip through without
a conscious `overridable=True` or `overridable=False` decision.

## Consequences

- `hasscheck.yaml` is the single override surface for v0.2.
- REQUIRED rules (9 locked) and mixed-status rules (2 locked) cannot be softened.
- Natural NOT_APPLICABLE overrides are silent no-ops (no count, no banner).
- `overrides_applied` is always present in JSON output (count=0, rule_ids=[]) —
  stable for downstream consumers that expect the key unconditionally.
