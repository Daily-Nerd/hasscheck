# diagnostics.redaction.used

## Summary

Checks that `diagnostics.py` uses `async_redact_data` from `homeassistant.components.diagnostics` or a local redaction helper (matched by name pattern `^_?redact(_.*)?$`) before returning diagnostic data. Uses AST static inspection.

## Why this matters

Home Assistant diagnostics expose integration state for troubleshooting. Without redaction, sensitive fields (API keys, tokens, passwords, coordinates) can be leaked when users share diagnostic downloads with maintainers or support channels. This rule checks for the most common patterns; it cannot detect redaction performed in a base class, mixin, or via dynamic dispatch — those cases may produce a false WARN. A WARN does NOT guarantee a bug; treat it as a prompt for manual review of the diagnostics output.

## Status behavior

| Condition | Status |
|---|---|
| No integration directory detected | NOT_APPLICABLE |
| `hasscheck.yaml` declares `supports_diagnostics: false` | NOT_APPLICABLE |
| `diagnostics.py` does not exist | NOT_APPLICABLE |
| `diagnostics.py` has a syntax error | WARN |
| `diagnostics.py` exists but has no diagnostics function | NOT_APPLICABLE |
| Diagnostics function returns `entry.data` / `entry.options` directly without redaction | WARN |
| `async_redact_data` or a matching local redaction helper is called | PASS |
| Diagnostics function exists, no raw return, no recognized redaction | WARN |

## How to fix

Use `async_redact_data` from `homeassistant.components.diagnostics` with a list of sensitive keys:

```python
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = ["api_key", "password", "token", "latitude", "longitude"]

async def async_get_config_entry_diagnostics(hass, entry):
    return async_redact_data(dict(entry.data), TO_REDACT)
```

Alternatively, use `hasscheck scaffold diagnostics --path <your-integration-path>` to generate a starter file with a local redaction helper.

## Applicability / overrides

Overridable via `hasscheck.yaml` (severity: RECOMMENDED). To declare the integration does not expose diagnostics:

```yaml
applicability:
  supports_diagnostics: false
```

Or to override just this rule:

```yaml
rules:
  diagnostics.redaction.used:
    status: manual_review
    reason: Redaction is performed in the shared base class DiagnosticsMixin.
```

## Source

- HA dev docs: https://developers.home-assistant.io/docs/core/integration/diagnostics/
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```python
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = ["api_key", "token"]

async def async_get_config_entry_diagnostics(hass, entry):
    return async_redact_data(dict(entry.data), TO_REDACT)
```

### Failing / warning

```python
async def async_get_config_entry_diagnostics(hass, entry):
    # Returns raw entry data — likely exposes secrets
    return dict(entry.data)
```

HassCheck reports WARN because `entry.data` is returned without redaction.
