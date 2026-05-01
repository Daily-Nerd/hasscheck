# ADR 0006 — Ruleset versioning: DEFAULT_RULESET_ID and DEFAULT_SOURCE_CHECKED_AT bump policy

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.6 stability

## Context

`models.py` exposes two module-level constants that appear in every JSON report
and in the `ruleset` block of the schema:

```python
DEFAULT_RULESET_ID = "hasscheck-ha-YYYY.MINOR"
DEFAULT_SOURCE_CHECKED_AT = "YYYY-MM-DD"
```

Without a documented policy, contributors bump these on every PR that touches
rules — or never bump them at all. Both outcomes corrupt downstream consumers
(badges, hosted reports, diffs) that rely on these values to detect meaningful
changes in rule coverage or source accuracy.

## Decisions

### DEFAULT_RULESET_ID

**Format:** `hasscheck-ha-YYYY.MINOR`

- `YYYY` = calendar year the bump happens.
- `MINOR` = integer, increments on each substantive update within that year.
  Resets to `1` when the year changes.

**Bump when (and only when):**

1. A new rule is added to any rules module.
2. An existing rule is updated because the underlying Home Assistant or HACS
   documentation it is sourced from has changed — i.e. the *rule intent* or
   *applicability logic* changed, not just the code around it.

The bump signals to JSON consumers: "the set of checks or their meaning has
changed since the last version."

### DEFAULT_SOURCE_CHECKED_AT

**Format:** `YYYY-MM-DD` (ISO 8601)

**Bump when (and only when):**

Someone manually re-verifies that every `source_url` referenced by the current
ruleset is still live, still accurate, and still the canonical reference for
the rule it backs. This is a deliberate human action, not a code change.

The date signals to consumers: "as of this date, all source URLs were verified
accurate."

## What does NOT trigger a bump

The following changes MUST NOT update either constant:

- Refactoring `models.py`, `checker.py`, `output.py`, or any other non-rule
  module.
- Fixing a checker bug where the rule logic was wrong but the rule *intent*
  did not change (e.g. a regex error, a wrong path comparison).
- Adding a new field to `HassCheckReport`, `Finding`, or `RulesetInfo`.
- Reformatting or linting rule files (black, ruff, isort).
- Adding or updating tests, documentation, or ADRs.
- Changing CLI help text, error messages, or exit codes.
- Adding a new scaffold subcommand.

## Reasoning

- **Semantic signal, not syntactic trigger.** Bumping on every code change
  makes the version meaningless — consumers cannot tell whether the rule
  surface changed or someone just ran a linter. Both constants must carry
  semantic weight.
- **Source accuracy is a separate concern from rule coverage.** A rule can
  exist and be correct even if its source URL moved. Conflating the two would
  require bumping `DEFAULT_RULESET_ID` every time a docs URL changes, which
  again destroys the semantic signal.
- **Human gate on source verification.** `DEFAULT_SOURCE_CHECKED_AT` is
  intentionally not automated. A CI job cannot verify that the *content* of a
  source URL still matches the rule. A human must read the source and confirm.

## Consequences

### Positive

- JSON consumers can use `ruleset.id` to detect meaningful rule surface changes
  and update their dashboards, badges, or stored reports accordingly.
- `ruleset.source_checked_at` gives consumers a freshness signal for rule
  sourcing independent of rule coverage.
- Contributors have a clear checklist: "did I add or meaningfully change a
  rule? If yes, bump the ID."

### Negative

- Requires contributor discipline to bump correctly. Reviewers must check.
- The MINOR counter is per-year and resets, so `hasscheck-ha-2027.1` is newer
  than `hasscheck-ha-2026.12`. Consumers that sort lexicographically will get
  the wrong order across year boundaries (they must parse YYYY and MINOR
  separately).

## Alternatives considered

- **Semver for ruleset ID** — rejected. Semver implies backward compatibility
  semantics that do not map cleanly onto "a new check was added." The current
  format is more self-documenting and ties the version to a calendar year,
  which matches the HA/HACS release cadence.
- **Auto-bump on any rules/ file change** — rejected. Refactors and bug fixes
  in rule checkers do not change what the rule checks for. Auto-bump would
  inflate the version and break the semantic contract.
- **Bump both constants together** — rejected. Source URL accuracy and rule
  coverage are independent. Forcing a co-bump creates false precision (e.g.
  "sources were verified" when only a new rule was added).
