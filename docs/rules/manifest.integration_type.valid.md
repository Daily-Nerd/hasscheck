# manifest.integration_type.valid

## Summary

Checks that the `integration_type` field in `manifest.json` is one of the canonical values defined in the Home Assistant integration manifest docs. An unrecognised value is rejected by the core manifest loader in newer HA versions.

## Why this matters

`integration_type` classifies how the integration fits into the Home Assistant architecture — as a hub managing devices, a helper that processes data, a hardware-level driver, and so on. Newer HA versions actively reject unknown values at manifest load time, which can prevent the integration from loading. Custom integrations default to `"hub"` when the field is omitted, but a present-but-invalid value is worse than absent.

## Status behavior

| Condition | Status |
|---|---|
| No integration directory detected | NOT_APPLICABLE |
| `manifest.json` is missing | NOT_APPLICABLE |
| `manifest.json` is invalid JSON | NOT_APPLICABLE (exists rule handles FAIL) |
| `integration_type` field is absent | NOT_APPLICABLE |
| `integration_type` value is a recognized value | PASS |
| `integration_type` value is not a recognized value | FAIL |

## How to fix

Set `integration_type` in `manifest.json` to one of the following recognized values:

- `device`
- `entity`
- `hardware`
- `helper`
- `hub`
- `service`
- `system`
- `virtual`

Most custom integrations that talk to an external service or device should use `"hub"`.

## Applicability / overrides

Overridable via `hasscheck.yaml` (severity: RECOMMENDED). Add the following to opt out:

```yaml
rules:
  manifest.integration_type.valid:
    status: not_applicable
    reason: <your reason>
```

This rule is only evaluated when `integration_type` is present. If the field is absent, `manifest.integration_type.exists` warns first.

## Source

- HA dev docs: https://developers.home-assistant.io/docs/creating_integration_manifest
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```json
{
  "domain": "my_sensor",
  "integration_type": "hub"
}
```

### Failing

```json
{
  "domain": "my_sensor",
  "integration_type": "appliance"
}
```

HassCheck reports FAIL because `"appliance"` is not a recognized value.
