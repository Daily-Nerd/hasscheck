# ADR 0002 — Block A (project applicability flags) deferred to v0.3

- **Status**: Accepted
- **Date**: 2026-04-30
- **Tag**: v0.2 scope

## Context

The original brief (`idea.md` section 6, Decision 1) shows
`hasscheck.yaml` with two blocks:

```yaml
applicability:                  # Block A: project-level flags
  auth_required: false
  has_devices: true
  cloud_service: false
  uses_config_entry: true

rules:                          # Block B: per-rule overrides
  repairs.file.exists:
    status: not_applicable
    reason: No user-fixable repair scenario yet.
```

These look like one feature in the brief but are two completely
different beasts:

- **Block B** is a config feature — the user explicitly skips a rule
  with a written reason. The override logic lives in one new module
  (`config.py`) and applies at finding time.
- **Block A** is something else — the user declares project context
  and **rules are expected to read those flags** to decide their own
  applicability. So `repairs.file.exists` would see `auth_required:
  false` and auto-mark itself `not_applicable` without the user
  touching Block B at all. The logic lives **inside every applicable
  rule's `check()` function.**

## Decision

Ship only Block B in v0.2. Defer Block A — and the related
applicability auto-detection — to v0.3.

## Reasoning

- **Block A without rule consumers is dead config.** If users declare
  flags and no rule reads them, the flags do nothing. That is worse
  than not having them.
- **Block A is a rule-engine upgrade, not a config feature.** Every
  applicable rule's `check()` would need to read flags and decide
  applicability, and we'd need test coverage for every flag/rule
  combination. That is an order of magnitude larger than Block B.
- **The brief itself separates them.** Section 6 introduces the
  override mechanism (Block B). Section 15 ("Month 2") lists
  *Applicability detection* as a separate deliverable. Treat them as
  separate deliverables.
- **Block B alone solves the v0.2 pain.** Maintainers can say "this
  rule does not apply to my integration, here's why" and move on.
  That is the v0.2 promise, fulfilled cleanly.

## Consequences

### Positive

- v0.2 stays small, shippable, and honest about what it adds.
- Block A's design space stays open. We can ship it in v0.3 alongside
  auto-detection — where it has rules to talk to.
- Forcing maintainers to write per-rule overrides with explicit
  reasons in v0.2 generates real-world data on which rules trip
  context-sensitivity most often. That data informs the Block A
  schema in v0.3.

### Negative

- Maintainers with context-dependent integrations write tedious
  per-rule entries in Block B for the same 3-4 rules. Honest friction
  — they have to think about what doesn't apply and write it down with
  a reason. Block A would automate that, at 10x cost and with the
  risk that auto-detection gets it wrong silently.

## Trigger to revisit

Revisit when **either**:

1. v0.3 starts and applicability auto-detection enters scope, **or**
2. Block B usage shows that 80%+ of maintainers are writing the same
   3-4 overrides — a clear signal that the friction has crossed from
   honest to costly.
