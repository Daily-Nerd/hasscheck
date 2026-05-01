# docs.installation.exists

## Summary

Checks that the repository README contains a recognisable Installation section by scanning headings for installation-related keywords. A missing installation section means users have no in-repo guidance for adding the integration via HACS or manually.

## Why this matters

A README installation section guides users through HACS or manual setup. Without it, users must guess the setup path or find instructions elsewhere, increasing support requests and reducing adoption. This rule uses a conservative heading-only heuristic — it scans Markdown headings, bold solo lines, and emphasis solo lines outside code fences, and reports WARN only when no matching heading is found.

## Status behavior

| Condition | Status |
|---|---|
| README is missing | NOT_APPLICABLE |
| README has a heading matching an installation keyword | PASS |
| README exists but no matching heading found | WARN |

**Installation keywords** (whole-word match, case-insensitive): `installation`, `install`, `hacs`, `manual installation`, `manual install`.

## How to fix

Add an Installation section to `README.md`. Minimal example:

```markdown
## Installation

### Via HACS

1. Open HACS in your Home Assistant instance.
2. Search for "My Sensor".
3. Click Install.

### Manual

1. Copy `custom_components/my_sensor/` to your `custom_components/` directory.
2. Restart Home Assistant.
```

Any heading that contains one of the installation keywords will satisfy this rule.

## Applicability / overrides

Overridable via `hasscheck.yaml` (severity: RECOMMENDED):

```yaml
rules:
  docs.installation.exists:
    status: not_applicable
    reason: Installation instructions live in an external wiki.
```

## Source

- HA dev docs: https://developers.home-assistant.io/docs/documenting_integrations
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```markdown
## Installation

Install via HACS or manually by copying the integration folder.
```

### Failing / warning

```markdown
## My Sensor

A great sensor integration.
```

No heading contains `install`, `hacs`, or related keywords — HassCheck reports WARN.
