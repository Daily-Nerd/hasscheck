# ADR 0001 — Config override policy: locked vs softenable, never force-pass

- **Status**: Accepted
- **Date**: 2026-04-30
- **Tag**: v0.2 design

## Context

v0.2 introduces `hasscheck.yaml` so maintainers can override rule
findings on their projects. Two design questions are load-bearing:

1. **What direction can overrides move a finding?** Can a user force a
   `fail` to `pass`?
2. **Which rules are overridable at all?** Should foundational rules
   like `manifest.exists` be touchable from user config?

Anything `hasscheck.yaml` is allowed to do becomes part of the public
contract that v0.5 (badges), v0.7 (hosted reports), and v1.0 (project
hub) will read. Get this wrong and the entire trust story downstream
collapses.

## Decision

A two-axis policy.

### Axis 1 — Soften only

Overrides may move a finding only toward `not_applicable` or
`manual_review`. They may **never** force `pass` and may **never**
upgrade `warn` or `fail` to `pass`.

### Axis 2 — Per-rule `overridable` flag

Every rule carries an `overridable: bool` field in its definition.

- REQUIRED rules → `overridable = False` by default.
- RECOMMENDED rules → `overridable = True` by default.
- Correctness checks — rules that detect *bugs* rather than *presence*
  (e.g. `config_flow.manifest_flag_consistent`) — are explicitly
  `overridable = False` regardless of severity.

When a user attempts to override a non-overridable rule, `hasscheck`
exits with a clear error pointing at the offending entry.

## Reasoning

- **Forcing `pass` would let users lie to the tool.** The JSON contract
  becomes a self-report; "HACS Checks: Passing" badges mean "the
  user said so" rather than "checks passed." Directly contradicts the
  "False authority" HIGH-severity risk in `idea.md` section 18.
- **Some rules detect lies, not absences.**
  `config_flow.manifest_flag_consistent` is a correctness check — if
  `config_flow.py` exists but the manifest says `config_flow: false`,
  the integration is broken. Letting the user override it hides a real
  runtime bug from CI, badges, and themselves.
- **Per-rule `overridable` is more honest than a global mode.** A
  global `strict_mode: true|false` is coarse and opaque. The right
  granularity is per-rule, because the answer to "is this softenable?"
  varies rule by rule.
- **The mental model fits in one sentence.** *REQUIRED rules are
  locked, RECOMMENDED rules are softenable, you can never force a
  PASS.* Users read that and know everything.

## Consequences

### Positive

- "Automated checks passed" stays honest. v0.5 badges can show a
  green PASS without lying.
- Correctness checks cannot be silenced. Real bugs surface on
  configured projects too.
- `applicability.source: "config"` discloses which findings were
  overridden, so JSON consumers can trust what they're trusting.
- The locked list lives in code, not user config. Edge cases come
  back as bug reports and the softenable set widens with judgment —
  the right place for that conversation.

### Negative

- Maintainers with edge cases on REQUIRED rules have no escape hatch.
  By design.
- One additional field per rule definition (`overridable`).

## Alternatives considered

- **Full override** (any rule, any direction) — rejected. Lets users
  lie back to the tool, poisoning every downstream JSON consumer.
- **Global `strict_mode` flag** — rejected. Wrong granularity; some
  rules are correctness checks regardless of how strict the user wants
  to be.
- **Soften only, but no locked rules** — rejected. Even with soften
  only, allowing `manifest.exists` to be marked `not_applicable` would
  let users opt out of the integration's identity. Some things are
  not contextual.
