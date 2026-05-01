# ADR 0007 — Badge policy: opt-in only, forbidden language, layered-status contract

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.6 badges

## Context

v0.6.0 introduces `hasscheck badge`, a command that writes shields.io endpoint
JSON files so maintainers can embed specific quality signals in their READMEs.

Three design questions are load-bearing:

1. **Should badges be emitted by default?** Running `hasscheck check` or the
   GitHub Action without opt-in should produce no badge files — they require
   the maintainer to decide where and how to host JSON files.
2. **What language is allowed on badge labels and messages?** `idea.md` §12
   identifies "False authority" as a HIGH-severity risk. Vague terms like
   "certified" or "safe" must be prevented at the code level, not left to
   contributor judgment.
3. **What happens when all rules in a category are `not_applicable`?** Emitting
   a badge for a category that was never evaluated would misrepresent coverage.

ADR 0001 already commits to honest language (overrides may never force a
`pass`). ADR 0004 already commits to layered, post-applicability status
(categories with all rules `not_applicable` produce no meaningful aggregate).
This ADR extends both contracts to the badge surface.

## Decision

### Opt-in only

Badges are **never** emitted by default. Neither `hasscheck check` nor the
GitHub Action emits badge files unless the caller explicitly opts in:

- CLI: `hasscheck badge --path . --out-dir badges/`
- Action: `emit-badges: 'true'` input on `Daily-Nerd/hasscheck`

There is no configuration key in `hasscheck.yaml` that silently enables badge
generation on every run.

### Frozen forbidden-language blocklist

Badge label and message text is governed by `FORBIDDEN_LABEL_TOKENS` in
`src/hasscheck/badges/policy.py`:

```
certified, safe, approved, hacs ready, community ready
```

`assert_label_is_clean(label)` checks every label string against this list at
runtime. If any label contains a forbidden token (case-insensitive),
`BadgePolicyError` is raised immediately. A property test in
`tests/test_badges_policy.py` enforces this on every release — a violation is
a release-blocker.

### Allowed message suffixes

The only valid message strings are those in `ALLOWED_SUFFIXES`
(`src/hasscheck/badges/policy.py`):

```
Passing, Partial, Issues, Present, Missing, Signals Available
```

No other message text is permitted. This keeps badge vocabulary small,
consistent, and honest.

### Present/Missing for binary-presence categories

The `diagnostics_repairs` and `modern_ha_patterns` categories use
`Present`/`Missing` instead of `Passing`/`Issues`. These categories check for
the *presence* of files and patterns — "Passing" would imply a quality bar
that a file-existence check cannot support.

### Post-applicability layered status

Badges consume the post-applicability aggregate status (per ADR 0004). A
category where every rule returned `not_applicable` emits **no badge file**.
Emitting a badge for a category that was never evaluated would assert a signal
that was never produced.

### Config overrides propagate honestly

Config overrides applied via `hasscheck.yaml` are reflected in badge state (per
ADR 0001). If a finding's status changes because of an override, that change
propagates through to the category aggregate and therefore to the badge color.
The badge shows what the tool actually concluded — not what it would have
concluded without the config.

### Umbrella badge is descriptive only

The umbrella `hasscheck.json` badge always shows `HassCheck: Signals Available`
in `lightgrey`. It carries no pass/fail signal. It is a presence indicator:
"this repository has been checked." Any interpretation of quality must come
from the per-category badges.

## Consequences

### Positive

- Maintainers can embed shields.io badges that show specific, honest signals.
- The forbidden-language list is enforced at runtime and by a property test —
  no contributor can accidentally introduce a vague trust claim.
- The opt-in gate means no badge files appear unexpectedly in repositories that
  do not want them.
- N/A categories produce no badge, so the absence of a badge file is
  informative (the category was not evaluated) rather than misleading.

### Negative

- Maintainers must explicitly invoke `hasscheck badge` or set `emit-badges:
  'true'` — there is no automatic badge on every run.
- Badge JSON files must be hosted somewhere publicly accessible (committed to
  the repository or published to GitHub Pages) for shields.io to read them.
  This is an operational step the maintainer must own.
- The blocklist is frozen in code — adding a new forbidden token is a code
  change, not a configuration change.

## References

- ADR 0001 — Config override policy: locked vs softenable, never force-pass
- ADR 0004 — Layered applicability status (post-applicability aggregation)
- `idea.md` §12 — False authority risk (HIGH severity)
- `src/hasscheck/badges/policy.py` — `FORBIDDEN_LABEL_TOKENS`, `ALLOWED_SUFFIXES`,
  `CATEGORY_LABELS`, `BADGE_MANIFEST_SCHEMA_VERSION`
- `tests/test_badges_policy.py` — property test enforcing the blocklist
