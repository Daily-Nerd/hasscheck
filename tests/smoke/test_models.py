"""Group 4: Tests for hasscheck.smoke.models — internal dataclasses."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest


def test_probe_target_is_frozen_dataclass() -> None:
    """ProbeTarget is a frozen dataclass with module: str and file_path: Path."""
    from hasscheck.smoke.models import ProbeTarget

    assert dataclasses.is_dataclass(ProbeTarget)
    fields = {f.name: f for f in dataclasses.fields(ProbeTarget)}
    assert "module" in fields
    assert "file_path" in fields
    # frozen → assignment raises FrozenInstanceError
    t = ProbeTarget(module="custom_components.foo", file_path=Path("/foo/__init__.py"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.module = "other"  # type: ignore[misc]


def test_probe_target_field_types() -> None:
    """ProbeTarget.module is str and file_path is Path."""
    from hasscheck.smoke.models import ProbeTarget

    t = ProbeTarget(module="custom_components.foo", file_path=Path("/foo/__init__.py"))
    assert isinstance(t.module, str)
    assert isinstance(t.file_path, Path)


def test_run_smoke_result_is_frozen_dataclass() -> None:
    """RunSmokeResult is a frozen dataclass with the required fields."""
    import dataclasses

    from hasscheck.smoke.models import RunSmokeResult

    assert dataclasses.is_dataclass(RunSmokeResult)
    fields = {f.name for f in dataclasses.fields(RunSmokeResult)}
    assert "ha_version" in fields
    assert "python_version" in fields
    assert "report" in fields
    assert "venv_reused" in fields


def test_run_smoke_result_is_not_pydantic() -> None:
    """RunSmokeResult must NOT be a Pydantic BaseModel."""
    from hasscheck.smoke.models import RunSmokeResult

    try:
        from pydantic import BaseModel

        assert not issubclass(RunSmokeResult, BaseModel)
    except ImportError:
        pass  # pydantic not installed — trivially satisfied


def test_probe_target_is_not_pydantic() -> None:
    """ProbeTarget must NOT be a Pydantic BaseModel."""
    from hasscheck.smoke.models import ProbeTarget

    try:
        from pydantic import BaseModel

        assert not issubclass(ProbeTarget, BaseModel)
    except ImportError:
        pass
