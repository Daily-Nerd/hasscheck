# Compatibility Claim Policy

> **HassCheck compatibility reports are exact-build signals.**
>
> A report applies only to the integration version, commit SHA, Home Assistant
> version, Python version, check mode, HassCheck version, and ruleset shown in
> the report.
>
> Reports for older integration versions or older Home Assistant versions are
> historical signals only. They do not imply compatibility for newer integration
> or Home Assistant releases.

This document is the public wording contract for every consumer of HassCheck
output — the CLI, the GitHub Action, the hosted hub at
[hasscheck.io](https://hasscheck.io), badges, dashboards, and any downstream
tool that surfaces a HassCheck report. If you display, summarise, or link to a
HassCheck report, follow the rules below.

The rationale is recorded in
[ADR 0012 — Compatibility claim policy](decisions/0012-compatibility-claim-policy.md).

---

## 1. The exact-build claim

A HassCheck report is a **point-in-time signal about a specific build**. It is
not a general statement about an integration. Every report carries the exact
identity of what was checked:

- The integration version (manifest `version`, git tag, or release identity)
- The commit SHA
- The Home Assistant version it was checked against (when populated by the
  caller — see [Status taxonomy](#3-status-taxonomy))
- The Python version of the runner
- The HassCheck version and ruleset ID
- The check mode (`local`, `ci-published`, or `server-verified` — see
  [Trust levels](#5-trust-levels))

A new commit, a new HA release, a new HassCheck version, or a different ruleset
produces a **different report**. Older reports do not transfer.

## 2. Wording rules

When you talk about a report, use the language below. The bad examples are
forbidden in HassCheck-owned surfaces (CLI output, hub UI, badges, official
docs) and discouraged everywhere else.

| | Phrase |
|---|---|
| Never | "Integration X is compatible with HA 2026.5" |
| Never | "X works with HA 2026.5" |
| Never | "X is HA 2026.5 ready" |
| Always | "Version 2.5.0 was checked against HA 2026.5.1" |
| Always | "Latest verified report for version 2.5.0 against HA 2026.5.1 has warnings" |
| Always | "No verified report exists for version 1.3.0 against HA 2026.5.1" |
| Always | "Version 2.5.0 last passed against HA 2026.5.1 on 2026-05-02" |

The pattern is: **<integration version> was checked against <HA version> at
<time> with <result>**. Never collapse it to "X is compatible with Y".

## 3. Status taxonomy

Every HassCheck consumer that surfaces a verdict for an `(integration version,
HA version)` pair MUST use one of the labels below. No new labels, no
synonyms.

| Status | Meaning |
|---|---|
| `PASS` | Exact integration version checked against exact HA version recently. No failures, no warnings. |
| `WARN` | Exact integration version checked against exact HA version, recommended-rule warnings found. |
| `FAIL` | Exact integration version checked against exact HA version, required-rule failures found. |
| `STALE` | Exact integration version checked against exact HA version, but report is older than 90 days. |
| `SUPERSEDED` | This integration version passed, but newer integration versions exist. Latest version may differ. |
| `NOT_CHECKED` | No report exists for this `(integration version, HA version)` pair. |
| `UNKNOWN_VERSION` | Report exists but the integration version could not be determined from the report. |
| `VERSION_MISMATCH` | Manifest `version`, git tag, or release identity do not agree for the same report. |

`PASS`, `WARN`, and `FAIL` are produced directly by the HassCheck rules engine.
The remaining statuses (`STALE`, `SUPERSEDED`, `NOT_CHECKED`, `UNKNOWN_VERSION`,
`VERSION_MISMATCH`) are produced by the consumer (typically the hub) when it
indexes reports across versions and time.

## 4. Confidence levels

When a consumer looks up the "best" report for an `(integration version, HA
version)` pair and the exact match is missing, it MAY surface the nearest
verified report — but only with an explicit confidence label.

| Confidence | Meaning |
|---|---|
| `exact` | Same integration version, same HA version. |
| `patch-nearby` | Same integration version, nearby HA patch version (same minor). |
| `version-stale` | Same integration version, older HA version (different minor or major). |
| `integration-superseded` | Older integration version checked, newer integration release exists. |
| `unknown` | No useful verified report. |

Anything below `exact` is a **navigation aid**, not a compatibility claim.
Display the exact identity of what was actually checked — never paper over the
mismatch.

## 5. Trust levels

HassCheck reports come from three execution contexts. Consumers MUST display
the trust level prominently and MUST NOT treat lower levels as equivalent to
higher levels.

| Level | Meaning |
|---|---|
| `local` | Maintainer ran HassCheck locally. Self-reported. The publisher controls everything in the report. |
| `ci-published` | GitHub Actions ran HassCheck and the hub verified repository identity via OIDC at publish time. The repo identity is attested; the report contents are not re-executed by the hub. |
| `server-verified` | HassCheck Hub cloned the commit and re-ran the checks itself. The report contents are independently produced by the hub. |

This matches the Three-Trust-Levels model. See ADR 0012 for the rationale and
ADR 0010 for the OIDC verification mechanics that distinguish `local` from
`ci-published`.

## 6. Anti-inference rules

The following inferences are **forbidden** in any HassCheck-owned surface and
discouraged everywhere else. Each one is a wording trap that produces a false
compatibility claim.

> If version 2.5.0 passes HA 2026.5.1, you cannot conclude version 2.4.1
> passes.

> If version 1.3.0 passed HA 2025.4, you cannot conclude it passes HA 2026.5.

> If version 2.4.1 passed HA 2026.5, you cannot conclude version 2.5.0
> passes — even for tiny diffs — unless the diff is documented as
> docs/metadata-only.

> "Nearest verified report" is a navigation aid, not a compatibility claim.

If you find yourself wanting to bridge two reports, stop. Surface both reports
with their exact identities and let the reader make the call.

---

## Why this exists

A HassCheck report that is summarised as "X is compatible with HA Y" is worse
than no report at all: users trust it, integrations break under it, and the
trust collapses across every report HassCheck has ever emitted. The wording
rules above protect users from that failure mode by making the exact-build
nature of every report inescapable in language.

For the strategic and historical context, see
[ADR 0012 — Compatibility claim policy](decisions/0012-compatibility-claim-policy.md).
