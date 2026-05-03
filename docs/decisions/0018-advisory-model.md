# 0018 — Advisory Model

**Status:** Accepted
**Date:** 2026-05-02
**Issue:** #144

---

## Context

HassCheck rules need structured, versioned advisory metadata that can be consumed
by external tooling (hubs, CI dashboards, IDE plugins) without coupling that
tooling to Python code. Rules also need a stable cross-reference between a rule
ID and the upstream HA deprecation notice that motivated it.

---

## Decisions

### D1 — `Advisory(BaseModel, extra="forbid")`

Use a Pydantic model with `extra="forbid"` and `frozen=True` for advisory objects.
Fields: `id`, `introduced_in`, `enforced_in`, `source_url`, `title`, `summary`,
`affected_patterns`, `severity` (`Literal["info","warn","error"]`), `rule_ids`.

**Why over TypedDict/dataclass:** Pydantic is already a first-class dependency
(`HassCheckReport`). `extra="forbid"` catches YAML typos at import time.
`Literal["info","warn","error"]` validates severity declaratively.

### D2 — Eager module-level load

`ADVISORIES: dict[str, Advisory] = _load_all()` is evaluated at module import
time — not lazily. Matches the existing `RULES` pattern (eager). YAML files are
tiny and local. Import-time failures surface packaging issues loudly:
`FileNotFoundError`/`ValidationError` → `RuntimeError` with a descriptive message.

### D3 — YAML naming convention `ha-{year}-{month}-{slug}.yaml`

Advisory IDs match the file stem. Human-readable in registry tests and commits.
Aligns with HA release cadence (year.month). Alternative (sequential numbers)
would obscure the HA version relationship.

### D4 — Promote `_module_calls_name` to `ast_utils`

Promoted from `rules/config_flow._module_calls_name` to
`ast_utils.module_calls_name` (public). Six+ deprecation rules need it.
`config_flow.py` imports it under the old local name — zero behavior change.

### D5 — `severity=RECOMMENDED, overridable=True` for all 10 deprecation rules

Deprecation rules are warnings until `enforced_in` version. Integrations may
have legitimate reasons to suppress them (legacy compatibility, staged
migrations). Matches existing overridable RECOMMENDED pattern.

### D6 — All 10 rules in a single `rules/deprecations.py`

Consistent with `config_flow.py` (850+ LOC). All share AST utilities and the
same CATEGORY = "deprecations".

### D7 — Explicit import in `registry.py`

`from hasscheck.rules.deprecations import RULES as DEPRECATIONS_RULES` then
`*DEPRECATIONS_RULES` in main `RULES` list. Auto-discovery via `pkgutil` is
rejected: every rule module is explicitly listed — by project convention (D7).

### D8 — Bidirectional parity test

`tests/test_advisory_parity.py` asserts:
1. Every `rule.advisory_id` (non-None) has a matching key in `ADVISORIES`.
2. Every advisory in `ADVISORIES` is referenced by ≥1 rule's `advisory_id`.

Catches dead advisories AND broken rule references. Runs in milliseconds.

### D9 — Explicit `CATEGORY_LABELS` entry

`"deprecations": "HA Deprecation Advisories"` added to `checker.py`.
Fallback `.replace("_"," ").title()` would yield "Deprecations" (acceptable),
but explicit entry communicates intent and matches existing convention.

### D10 — `ha_version` is HUB-SIDE filtering metadata only

`min_ha_version` and `max_ha_version` on `RuleDefinition` are informational.
All 10 deprecation rules fire unconditionally at static check time.
`ProjectContext` does NOT gain an `ha_version` field in this change.
Hub/dashboard consumers filter by HA version using `Advisory.introduced_in`
and `Advisory.enforced_in`.

---

## Consequences

- 10 new `RECOMMENDED/overridable` rules in the `deprecations` category.
- Total rule count: 55 → 65.
- `ADVISORIES` dict is available at `from hasscheck.advisories import ADVISORIES`.
- Parity test (`test_advisory_parity.py`) enforces schema integrity in CI.
- No changes to `ProjectContext`, `Finding`, or existing rules.
