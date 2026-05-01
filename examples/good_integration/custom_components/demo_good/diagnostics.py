"""Diagnostics fixture for the HassCheck good integration example."""

from __future__ import annotations

TO_REDACT = {"api_key", "token", "password"}


async def async_get_config_entry_diagnostics(hass, config_entry):
    """Return placeholder diagnostics for fixture purposes."""
    return {"domain": config_entry.domain if config_entry else "demo_good"}
