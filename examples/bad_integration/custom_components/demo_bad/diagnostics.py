"""Intentionally bad diagnostics — returns entry.data without redaction.

This file is part of the bad_integration fixture used by hasscheck tests.
It intentionally violates best practices so tests can assert WARN findings.

Defect: returns entry.data directly without calling async_redact_data or
a local redaction helper — triggers diagnostics.redaction.used WARN with
raw-entry.data wording ("likely exposes secrets").
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics — intentionally missing redaction."""
    # BAD: returns entry.data directly, exposing API keys, tokens, passwords.
    return entry.data  # type: ignore[return-value]
