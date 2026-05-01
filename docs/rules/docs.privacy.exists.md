# docs.privacy.exists

## Summary

Checks that the repository README contains a recognisable privacy or data handling section by scanning headings for privacy-related keywords. Presence of this section signals that the maintainer considered what data the integration collects or transmits.

## Why this matters

A README privacy section shows users the maintainer considered data handling — whether the integration operates cloud vs. local, sends telemetry, or stores sensitive data. Integration Quality Scale guidelines expect maintainers to document this explicitly. Without it, users have no way to evaluate the integration's privacy posture before installing. This rule uses a conservative heading-only heuristic.

## Status behavior

| Condition | Status |
|---|---|
| README is missing | NOT_APPLICABLE |
| README has a heading matching a privacy keyword | PASS |
| README exists but no matching heading found | WARN |

**Privacy keywords** (whole-word match, case-insensitive): `privacy`, `data`, `telemetry`, `cloud`, `local`.

Note: `data` and `local` are broad — any heading containing these words (e.g. "Local data", "Data storage", "Cloud connectivity") satisfies the rule.

## How to fix

Add a Privacy or Data section to `README.md`. Minimal example:

```markdown
## Privacy

This integration communicates only with the local device at the configured IP address.
No data is sent to external servers or cloud services.
```

Or for a cloud-based integration:

```markdown
## Data

This integration uses the Example Cloud API. Device state is synced via the
vendor's cloud service. See the vendor's privacy policy for data retention details.
```

## Applicability / overrides

Overridable via `hasscheck.yaml` (severity: RECOMMENDED):

```yaml
rules:
  docs.privacy.exists:
    status: not_applicable
    reason: Privacy documentation lives in the integration's wiki.
```

## Source

- HA dev docs: https://developers.home-assistant.io/docs/documenting_integrations
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```markdown
## Local operation

This integration operates entirely on your local network and does not contact any cloud services.
```

The heading contains `local` — HassCheck reports PASS.

### Failing / warning

```markdown
## My Sensor

A great sensor integration.

## Installation

Install via HACS.
```

No heading contains `privacy`, `data`, `telemetry`, `cloud`, or `local` — HassCheck reports WARN.
