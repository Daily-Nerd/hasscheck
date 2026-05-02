# ADR 0012 — Compatibility claim policy: exact-build wording, status taxonomy, trust levels

- **Status**: Accepted
- **Date**: 2026-05-02
- **Tag**: v0.13.x (#154)

## Context

HassCheck is about to start emitting compatibility claims tied to specific
Home Assistant versions. The schema work in #141 (O1) introduces a `target`
block carrying `ha_version` and related identity fields, and the smoke harness
in O3 will exercise integrations against tagged HA versions to produce those
reports at scale. Once those land, every consumer — the CLI, the hosted hub at
[hasscheck.io](https://hasscheck.io), badges, the Upgrade Radar card, and any
downstream dashboard — starts surfacing version-tagged verdicts.

Without an explicit, public policy on what those verdicts mean, two failure
modes are guaranteed:

1. **Overclaiming**: a maintainer or automation reads "PASS for HA 2025.4" and
   tells users their integration is "compatible with HA 2025.4" — when actually
   the report applies only to one specific commit, integration version, Python
   version, check mode, HassCheck version, and ruleset.
2. **Underclaiming**: users dismiss valid signals because they don't understand
   a `STALE` or `SUPERSEDED` label, or because a consumer invented its own
   labels with different semantics.

The external pre-launch agent review (May 2026) flagged the wording rule as
the single most important contract HassCheck must publish before the first
version-tagged report ships. Once a single downstream surface uses the words
"compatible with HA X", that wording leaks across the ecosystem and is almost
impossible to recall.

The wording rule must precede emission. Not after. Not alongside.

## Decision

1. **HassCheck reports are exact-build signals.** A report applies only to the
   integration version, commit SHA, HA version, Python version, check mode,
   HassCheck version, and ruleset shown in the report. Reports for older
   integration versions or older HA versions are historical signals only. They
   do not imply compatibility for newer releases.

2. **The wording contract is published as a top-level docs page**:
   `docs/compatibility-claim-policy.md`. It is linked from the README's
   "How HassCheck relates to other tools" section so that anyone evaluating
   HassCheck encounters the wording rule before they encounter their first
   report.

3. **A canonical status taxonomy** is defined and frozen. Every consumer that
   surfaces an `(integration version, HA version)` verdict MUST use one of:

   `PASS`, `WARN`, `FAIL`, `STALE`, `SUPERSEDED`, `NOT_CHECKED`,
   `UNKNOWN_VERSION`, `VERSION_MISMATCH`.

   No synonyms, no new labels. Producer split:
   - `PASS`, `WARN`, `FAIL` are produced by the rules engine.
   - `STALE`, `SUPERSEDED`, `NOT_CHECKED`, `UNKNOWN_VERSION`,
     `VERSION_MISMATCH` are produced by the consumer (typically the hub) when
     it indexes reports across versions and time.

   This taxonomy is **distinct from** the Upgrade Radar taxonomy in ADR 0011
   (`fresh`, `warnings`, `failing`, `stale`, `unverified`). ADR 0011 governs
   the hub's per-integration aggregate signal computed from the latest
   hub-verified report. This ADR governs the per-`(integration version, HA
   version)` verdict displayed alongside an exact-build report. Both
   taxonomies coexist; the casing difference (UPPERCASE here vs. lowercase in
   ADR 0011) is intentional and contractual — it makes the surface
   unambiguous in code, in JSON, and in UI copy.

4. **A canonical confidence taxonomy** is defined for fallback lookups:
   `exact`, `patch-nearby`, `version-stale`, `integration-superseded`,
   `unknown`. Anything below `exact` is a navigation aid, not a compatibility
   claim. The exact identity of what was actually checked must always be
   displayed alongside the fallback.

5. **A canonical trust taxonomy** is adopted: `local`, `ci-published`,
   `server-verified`. This is the Three-Trust-Levels model. It is a separate
   axis from status and confidence. Lower trust levels MUST NOT be displayed
   as equivalent to higher trust levels. The trust level distinction is
   anchored in the OIDC mechanics from ADR 0010 (the hub's `verified_by`
   write-right is what separates `local` from `ci-published`).

6. **Anti-inference rules are part of the contract**, not a footnote. Forbidden
   inferences include:
   - "Version A passes HA X" → "Version A−1 passes HA X"
   - "Version A passes HA X" → "Version A passes HA X+1"
   - "Version A passes HA X" → "Version A+1 passes HA X" (even for tiny diffs)
   - "Nearest verified report" → "compatibility claim"

7. **The CLI report footer** SHOULD reference
   `docs/compatibility-claim-policy.md` whenever the report carries a
   populated `report.target.ha_version`. The footer is wired up in the same
   change that introduces `report.target` (#141). Adding a dead-coded footer
   in this ADR's change would either gate on a non-existent field or emit an
   unconditional footer that exceeds what the schema currently supports —
   neither is acceptable.

8. **Hub UI surfaces** (Upgrade Radar card, badge endpoints, project pages)
   MUST display a prominent banner or footer linking to this policy whenever
   they show a version-tagged verdict. This is enforced by the hub side issue
   tracked separately as W11.

## Consequences

- **Wording is locked before the first version-tagged report ships.** Any PR
  that introduces "compatible with HA X" wording on a HassCheck-owned surface
  MUST be rejected against this ADR.
- **#141 (O1) inherits the CLI footer task.** The schema PR that introduces
  `report.target.ha_version` is also responsible for emitting the policy-doc
  footer. This ADR's change does not modify CLI rendering.
- **Status taxonomy is frozen.** Adding a new status (e.g., `DEPRECATED`,
  `UNVERIFIED`) requires a follow-up ADR. Consumers may not invent local
  variants.
- **Trust levels are frozen.** Adding a fourth trust level (e.g., a
  third-party verifier) requires a follow-up ADR and almost certainly a
  schema bump in the same vein as ADR 0010's `verified_by`.
- **Hub coupling is loosened, not tightened.** The hub is free to evolve its
  internal indexing and presentation, but the labels it surfaces are
  contractual. A hub UI change that drops `STALE` or renames it to `OLD`
  violates the contract.
- **Translation guidance**: localised hub UIs MUST keep the canonical English
  label visible alongside any translation, since the labels are part of the
  contract and downstream tools may parse them.

## Alternatives considered

- **Wait until the first matrix ships before publishing the policy.** Rejected.
  Wording rules must precede emission. Once the first "compatible with HA X"
  phrase escapes into a release blog or social post, the contract is poisoned.
- **Bury the policy in CHANGELOG or a release note.** Rejected. A release-note
  contract is not a contract. It must be a top-level docs page linked from the
  README.
- **Skip the status taxonomy and define it later, alongside the matrix.**
  Rejected. The taxonomy IS the wording rule. Without it, every consumer
  invents its own labels and the contract fragments before it ships.
- **Add an unconditional CLI footer now**, regardless of whether the report
  has a target HA version. Rejected. Schema 0.4.0 has no `target` block;
  emitting a "see compatibility-claim-policy.md" footer on reports that carry
  no version-tagged verdict is misleading. The footer follows the schema
  field that justifies it, which lands in #141.
- **Add a dead-coded gated footer now** so #141 only has to flip a flag.
  Rejected. Dead code rots, gates drift, and the wiring is small enough that
  doing it in #141 is cleaner than splitting it across two PRs.

## Related

- ADR 0009 — Schema versioning policy (additive bump rule)
- ADR 0010 — Provenance block (`verified_by` is the OIDC trust boundary that
  separates `local` from `ci-published`)
- ADR 0011 — Upgrade Radar status taxonomy (the per-integration aggregate
  signal; distinct surface, distinct casing, distinct semantics)
- Issue #141 — `report.target.ha_version` schema work (O1) and the CLI footer
  that consumes this policy
- Issue #154 — This ADR's source issue
- Hub-side issue W11 — Hub UI banner referencing this policy
