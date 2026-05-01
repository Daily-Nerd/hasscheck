# config_flow.user_step.exists

## Summary

Checks that `config_flow.py` defines an `async_step_user` method using AST inspection. Without it, users cannot start integration setup from the Home Assistant UI (Settings → Devices & Services).

## Why this matters

`async_step_user` is the standard entry point for Home Assistant config flows initiated by the user from the UI. If `config_flow.py` exists but does not define this method, the integration cannot be set up interactively — users must configure it manually via `configuration.yaml`, which is increasingly unsupported by HACS and the HA ecosystem. Note: this rule uses static AST inspection and cannot detect `async_step_user` defined only in a base class, mixin, or via dynamic attribute assignment — those cases produce a false WARN.

## Status behavior

| Condition | Status |
|---|---|
| No integration directory detected | NOT_APPLICABLE |
| `hasscheck.yaml` declares `uses_config_flow: false` | NOT_APPLICABLE |
| `config_flow.py` does not exist | NOT_APPLICABLE |
| `config_flow.py` has a syntax error | WARN |
| `config_flow.py` defines `async_step_user` | PASS |
| `config_flow.py` does not define `async_step_user` | WARN |

## How to fix

Add `async_step_user` to your `ConfigFlow` class in `config_flow.py`:

```python
class MyIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="My Integration", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
```

See the [HA config flow handler docs](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#defining-the-flow) for the full pattern.

## Applicability / overrides

Overridable via `hasscheck.yaml` (severity: RECOMMENDED). If the integration intentionally uses only `configuration.yaml` setup:

```yaml
applicability:
  uses_config_flow: false
```

This marks both `config_flow.file.exists` and `config_flow.user_step.exists` as NOT_APPLICABLE.

## Source

- HA dev docs: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#defining-the-flow
- `source_checked_at`: 2026-05-01

## Examples

### Passing

```python
# custom_components/my_sensor/config_flow.py
from homeassistant import config_entries

class MySensorConfigFlow(config_entries.ConfigFlow, domain="my_sensor"):
    async def async_step_user(self, user_input=None):
        ...
```

### Failing / warning

```python
# custom_components/my_sensor/config_flow.py
from homeassistant import config_entries

class MySensorConfigFlow(config_entries.ConfigFlow, domain="my_sensor"):
    # async_step_user is missing — HassCheck reports WARN
    pass
```
