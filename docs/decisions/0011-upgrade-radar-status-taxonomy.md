# ADR 0011 — Upgrade Radar status taxonomy

- **Status**: Accepted
- **Date**: 2026-05-02
- **Tag**: v1.0 hub positioning

## Context

Home Assistant's documentation explicitly states that custom integrations are
community-maintained, not officially reviewed, not security-audited, and not
supported by the Home Assistant project. Users who discover an integration
through HACS have no standardised signal for "is this integration being
maintained and does it pass basic quality checks right now?"

HassCheck's hub (via ADR 0008) accepts opt-in published reports from
maintainers who run the CLI in GitHub Actions with OIDC authentication. Each
published report carries a `provenance` block (ADR 0010) that records which
CI context produced it. This gives the hub a verified, time-stamped stream of
quality snapshots per integration.

Without a defined status model, a hub project page cannot answer the user
question clearly:

> "Can I trust this integration enough before I install or upgrade?"

A single score invites arguments. A five-state taxonomy aligned to recency and
finding severity is simpler to interpret and avoids false precision.

## Decision

### Status taxonomy

Five states, computed server-side on the hub from the most recent
hub-verified report for a given slug:

| State | Label | Calculation rule |
|-------|-------|-----------------|
| `fresh` | Fresh | Latest report ≤ 30 days old AND no `fail` findings AND ruleset matches current default |
| `warnings` | Warnings | Latest report ≤ 90 days old AND no `fail` findings AND ≥ 1 `warn` finding (or ruleset behind current) |
| `failing` | Failing | Latest report has ≥ 1 `fail` finding (regardless of age) |
| `stale` | Stale | Latest report > 90 days old AND no `fail` findings |
| `unverified` | Unverified | No hub-verified report ever published for this slug |

Priority when multiple rules apply: `failing` > `stale` > `warnings` > `fresh`.
`unverified` applies only when no record exists at all.

### Window rationale

- **30 days** (`fresh` upper bound): one sprint cycle. An integration updated
  within a month is demonstrably active.
- **90 days** (`stale` lower bound): one quarter. Beyond this, the signal is
  "this may be abandoned" regardless of historical pass state. The 30–90 day
  window surfaces as `warnings` — active but not freshly verified.
- These thresholds are initial best-guesses and SHOULD be tuned post-launch
  with real data. They are hub configuration, not OSS constants — no
  `SCHEMA_VERSION` bump is required to change them.

### Display contract

Hub project pages MUST:

- Show the status label and the date of the latest verified report
- Show the ruleset ID from that report (`hasscheck-ha-2026.5` etc.)
- Show finding counts (pass / warn / fail / not_applicable)
- Link to the full report page

Hub project pages MUST NOT:

- Use language like "certified", "safe", "approved", "official", or
  "HACS guaranteed"
- Imply security review was performed
- Imply compatibility with any specific HA version
- Display a numeric score as the primary signal

### CLI behaviour

Status is computed server-side only. `hasscheck check` and
`hasscheck publish --dry-run` do not display a radar status — they display
raw finding counts. This is intentional: the radar status depends on recency
(wall-clock time since last publish), which the CLI cannot compute without
querying the hub.

### `verified_by` contract

Per ADR 0010: the `provenance.verified_by` field is set exclusively by the
hub after OIDC validation passes. The CLI always emits `verified_by: null`.
The radar status MUST only be derived from reports where
`provenance.verified_by` is non-null. Self-reported local reports (uploaded
without OIDC) result in `unverified`.

## Consequences

**Positive**:
- Simple five-state model maps cleanly to a hub badge (`radar.json` endpoint
  consumed by shields.io).
- Maintainers have a clear action: publish a new report to move from `stale`
  to `warnings` or `fresh`.
- Users get a time-anchored signal without false precision.

**Negative**:
- Thresholds (30d / 90d) are best-guesses; will need tuning post-launch.
- `stale` may mis-signal stable integrations that haven't needed changes —
  the display label should clarify "last verified" rather than "abandoned".
- Status calculation is hub-side only — cannot be reproduced locally from
  the OSS CLI alone.

## References

- ADR 0008 — hosted reports publish contract
- ADR 0010 — provenance block and `verified_by` contract
- Issue #67 — hub-verified badges
- Issue #132 — Upgrade Radar positioning and this ADR
- hasscheck-web: radar card on project page (companion implementation issue)
