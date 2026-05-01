# manifest.domain.matches_directory

## Summary

Checks that the `domain` field in `manifest.json` matches the name of the integration directory under `custom_components/`. A mismatch causes Home Assistant to silently misidentify the integration, breaking HACS discovery and core platform loading.

## Why this matters

Home Assistant uses the integration directory name as the authoritative domain identifier. When `manifest.json` declares a different domain, the platform loader and HACS treat them as two separate entities. This mismatch is silent — no error is thrown at install time — so integrations can appear to load while being unreachable by domain-dependent features. This rule cannot be overridden via `hasscheck.yaml`.

## Status behavior

| Condition | Status |
|---|---|
| No integration directory (`custom_components/<domain>/`) detected | NOT_APPLICABLE |
| `manifest.json` is missing | NOT_APPLICABLE |
| `manifest.json` is invalid JSON | FAIL |
| `manifest.domain` matches the directory name | PASS |
| `manifest.domain` does not match the directory name | FAIL |

## How to fix

Rename the integration directory to match `manifest.domain`, or update `manifest.domain` to match the existing directory name. Both sides must agree on the same stable domain string.

## Applicability / overrides

This rule is **not overridable** via `hasscheck.yaml`. The domain-directory consistency is a structural requirement; no project-level flag changes its evaluation.

## Source

- HA dev docs: https://developers.home-assistant.io/docs/creating_integration_manifest
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```json
// custom_components/my_sensor/manifest.json
{
  "domain": "my_sensor",
  "name": "My Sensor"
}
```

The directory is `my_sensor/` and the manifest domain is `"my_sensor"` — they agree.

### Failing

```json
// custom_components/my_sensor/manifest.json
{
  "domain": "wrong_domain",
  "name": "My Sensor"
}
```

The directory is `my_sensor/` but the manifest domain is `"wrong_domain"` — HassCheck reports FAIL.
