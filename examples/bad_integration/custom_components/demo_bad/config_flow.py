"""Intentionally defective config flow — triggers config_flow.user_step.exists WARN.

This file defines an async setup step named `async_step_setup` instead of the
required `async_step_user`. Home Assistant requires `async_step_user` as the
entry point for user-initiated config flow setup.

See: examples/bad_integration/README.md for the full list of intentional defects.
"""

from __future__ import annotations


class DemoBadConfigFlow:
    """Config flow that intentionally omits async_step_user."""

    VERSION = 1

    async def async_step_setup(self, user_input=None):
        """Wrong step name — should be async_step_user."""
        return {}
