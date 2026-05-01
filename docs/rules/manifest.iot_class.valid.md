# manifest.iot_class.valid

## Summary

Checks that the `iot_class` field in `manifest.json` is one of the canonical values defined in the Home Assistant integration manifest docs. An unrecognised value may cause HA to silently ignore the field or display incorrect information.

## Why this matters

`iot_class` tells Home Assistant and users how the integration fetches data — whether it polls or uses push, and whether the connection is to a cloud service or local device. HA may use this to set UI expectations around connectivity and latency. Supplying an unrecognised value means the field is effectively absent, and users see no connectivity classification.

## Status behavior

| Condition | Status |
|---|---|
| No integration directory detected | NOT_APPLICABLE |
| `manifest.json` is missing | NOT_APPLICABLE |
| `manifest.json` is invalid JSON | NOT_APPLICABLE (exists rule handles FAIL) |
| `iot_class` field is absent | NOT_APPLICABLE |
| `iot_class` value is a recognized value | PASS |
| `iot_class` value is not a recognized value | FAIL |

## How to fix

Set `iot_class` in `manifest.json` to one of the following recognized values:

- `assumed_state`
- `calculated`
- `cloud_polling`
- `cloud_push`
- `local_polling`
- `local_push`

Choose the value that most accurately describes how your integration retrieves state from the device or service.

## Applicability / overrides

Overridable via `hasscheck.yaml` (severity: RECOMMENDED). Add the following to opt out:

```yaml
rules:
  manifest.iot_class.valid:
    status: not_applicable
    reason: <your reason>
```

This rule is only evaluated when `iot_class` is present. If the field is absent, `manifest.iot_class.exists` warns first.

## Source

- HA dev docs: https://developers.home-assistant.io/docs/creating_integration_manifest
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```json
{
  "domain": "my_sensor",
  "iot_class": "local_polling"
}
```

### Failing

```json
{
  "domain": "my_sensor",
  "iot_class": "not_a_valid_class"
}
```

HassCheck reports FAIL with the list of recognized values.
