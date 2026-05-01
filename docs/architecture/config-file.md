# Config file: `hasscheck.yaml` (v0.2)

> Status: in design. This document evolves as v0.2 ships.

## Why

After v0.1.0 shipped 23 rules across 7 categories, RECOMMENDED rules
emit `warn` findings on integrations where the rule legitimately does
not apply (for example, `repairs.file.exists` warning on integrations
with no user-fixable repair scenarios).

Without an override mechanism, those warnings become nagging lint noise.
v0.2 introduces `hasscheck.yaml` so maintainers can declare, with a
written reason, that a rule does not apply to their project.

## Shape

```yaml
# hasscheck.yaml — at the repo root
project:
  type: integration

rules:
  repairs.file.exists:
    status: not_applicable
    reason: No user-fixable repair scenarios in this integration.

  diagnostics.file.exists:
    status: manual_review
    reason: Diagnostics planned but not yet implemented.
```

## What `hasscheck.yaml` can and cannot do

| Capability | Allowed? |
|---|---|
| Soften a finding to `not_applicable` (RECOMMENDED rule) | ✅ |
| Soften a finding to `manual_review` (RECOMMENDED rule) | ✅ |
| Force a finding to `pass` | ❌ never |
| Upgrade a `warn` or `fail` to `pass` | ❌ never |
| Override a REQUIRED rule | ❌ never |
| Override a correctness check (e.g. `config_flow.manifest_flag_consistent`) | ❌ never |

The full reasoning lives in
[`../decisions/0001-config-override-policy.md`](../decisions/0001-config-override-policy.md).

## What is NOT in v0.2

The original brief (`idea.md` section 6) shows two blocks in
`hasscheck.yaml`. Only Block B (per-rule overrides) ships in v0.2.

| Feature | Status |
|---|---|
| Per-rule overrides (Block B) | ✅ v0.2 |
| Project-level applicability flags (Block A — `auth_required`, `has_devices`, …) | ⏭️ deferred to v0.3 |
| Auto-detection of applicability from project code | ⏭️ deferred to v0.3 |
| Multi-integration support (multiple subdirs in `custom_components/`) | ⏭️ orthogonal, separate work |

See [`../decisions/0002-block-a-deferred-to-v03.md`](../decisions/0002-block-a-deferred-to-v03.md).

## JSON disclosure

When a finding's status is changed by `hasscheck.yaml`, the JSON output
discloses this explicitly so downstream consumers (badges, hosted
reports, the future hub) can see what was overridden:

```json
{
  "rule_id": "repairs.file.exists",
  "status": "not_applicable",
  "applicability": {
    "status": "not_applicable",
    "reason": "No user-fixable repair scenarios in this integration.",
    "source": "config"
  }
}
```

`applicability.source` values:

| Value | Meaning |
|---|---|
| `default` | The rule's built-in applicability decision (no override, no auto-detection). |
| `detected` | (v0.3) The rule auto-detected applicability from the project. |
| `config` | `hasscheck.yaml` overrode the finding. |

## Validation behavior (TBD)

Open questions to resolve during implementation:

- Locked-rule override attempts → hard fail with clear error (likely).
- Unknown `rule_id` references in config → warn-and-skip for graceful
  upgrade/downgrade UX (likely).
- Missing `reason` on an override → hard fail; reason is mandatory
  because the value is the audit trail.

These will be confirmed during the v0.2 design phase.
