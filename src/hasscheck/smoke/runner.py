"""Subprocess boundary for the smoke harness.

All subprocess.run calls in the smoke package go through run_command().
Monkeypatch hasscheck.smoke.runner.subprocess.run to intercept them in tests.
"""

from __future__ import annotations

pass
