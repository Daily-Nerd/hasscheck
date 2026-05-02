"""Demo integration — intentionally lacks async_setup_entry and runtime_data usage.

Used by hasscheck fixtures to exercise init.* rules.
"""

DOMAIN = "demo_bad"


def setup(hass, config):
    """Legacy synchronous setup — does not use config entries."""
    hass.data.setdefault(DOMAIN, {})
    return True
