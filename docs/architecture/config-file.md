# Config file: `hasscheck.yaml` (v0.2)

> Status: in design. This document evolves as v0.2 ships.

## Why

After v0.1.0 shipped 18 rules across 7 categories, RECOMMENDED rules
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
| Soften a `warn` finding to `not_applicable` (overridable rule) | ✅ |
| Soften a `warn` finding to `manual_review` (overridable rule) | ✅ |
| Soften a `fail` finding to `not_applicable` (overridable rule) | ✅ |
| Soften a `fail` finding to `manual_review` (overridable rule) | ✅ |
| Override a `pass` finding | ❌ ignored — stale-config stderr warning |
| Override a `not_applicable` finding | ❌ silent no-op — natural source wins (Q8) |
| Force a finding to `pass` | ❌ never |
| Upgrade a `warn` or `fail` to `pass` | ❌ never |
| Override a REQUIRED rule | ❌ hard fail |
| Override a correctness check (e.g. `config_flow.manifest_flag_consistent`) | ❌ hard fail |
| Override a mixed-status rule (e.g. `hacs.file.parseable`) | ❌ hard fail |

The full policy reasoning lives in
[`../decisions/0001-config-override-policy.md`](../decisions/0001-config-override-policy.md).

## Defense in depth

The override engine has five layers of defense to keep the JSON contract
honest:

| Layer | Mechanism |
|---|---|
| 1 | REQUIRED rules → `overridable=False` |
| 2 | Correctness checks → `overridable=False` explicitly (e.g. `config_flow.manifest_flag_consistent`) |
| 3 | Mixed-status rules → `overridable=False` (only `hacs.file.parseable` in v0.2) |
| 4 | `pass` findings → ignored by the override engine even on overridable rules |
| 5 | Disclosure: `summary.overrides_applied { count, rule_ids }` + per-finding `applicability.source: "config"` + mandatory `reason` text |

Math stays consistent with v0.1 (overridden findings excluded from
`points_possible`). Trust comes from disclosure, not punishment.

### Overridable rules in v0.2

Of the 18 v0.1 rules, **8 are overridable** by `hasscheck.yaml`:

```text
config_flow.file.exists       diagnostics.file.exists       repairs.file.exists
brand.icon.exists             docs.readme.exists            repo.license.exists
tests.folder.exists           ci.github_actions.exists
```

The other 10 are locked (9 REQUIRED + 1 mixed-status).

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

## Validation behavior

| Condition | Behavior | Exit code |
|---|---|---|
| Valid `hasscheck.yaml` | Apply overrides; emit findings normally | 0 |
| Missing `hasscheck.yaml` | No overrides; behavior identical to v0.1 minus the new JSON fields | 0 |
| Malformed YAML | Hard fail with parse error pointing at line/column | non-zero |
| Unknown `rule_id` in config | Warn to stderr (with `rule_id` and "ignored"); skip that entry; continue | 0 |
| Missing `reason` on an override | Hard fail (Pydantic validation; `reason` is required) | non-zero |
| Locked-rule override (`overridable=False`) | Hard fail with rule_id and the rule's `overridable: false` flag | non-zero |
| Override on a `pass` finding | Warn to stderr ("override for X was ignored because the rule already passes"); finding stays PASS; not counted in `summary.overrides_applied` | 0 |
| Override on a `not_applicable` finding | Silent no-op (natural source wins per Q8); not counted in `summary.overrides_applied` | 0 |
| `--no-config` flag | Skip `hasscheck.yaml` entirely; behavior identical to v0.1 minus the new JSON fields | 0 |
| Both `config=...` and `no_config=True` to `run_check` | Hard fail (conflicting intent) | non-zero |

Order of operations inside `apply_overrides`:

1. Iterate config entries.
2. If `rule_id` is unknown → warn-and-skip.
3. Else if rule is `overridable=False` → hard fail.
4. Else if natural status is `PASS` → warn-and-skip (stale config).
5. Else if natural status is `NOT_APPLICABLE` → silent no-op.
6. Else → apply override, set `applicability.source = "config"`, append to `overrides_applied.rule_ids`.

Locked-rule errors win over stale-PASS warnings when both could fire
(fail-fast). Tests assert STRUCTURAL elements of error/warning messages
(`rule_id` present, remediation hint present), not exact wording.
