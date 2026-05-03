"""Group 5.5: Tests for build_probe_targets — file-existence guard."""

from __future__ import annotations

from pathlib import Path


def _make_integration(
    tmp_path: Path, platforms: list[str], files: list[str]
) -> tuple[Path, dict]:
    """Create an integration directory with specified files and return (path, manifest)."""
    integration = tmp_path / "custom_components" / "foo"
    integration.mkdir(parents=True)
    # Always create __init__.py unless explicitly excluded
    for fname in files:
        (integration / fname).touch()
    manifest = {
        "domain": "foo",
        "name": "Foo",
        "platforms": platforms,
    }
    return integration, manifest


def test_domain_init_included_when_exists(tmp_path) -> None:
    """__init__.py is always included when it exists."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(
        tmp_path, platforms=[], files=["__init__.py"]
    )
    targets = build_probe_targets(integration, manifest)
    modules = [t.module for t in targets]
    assert "custom_components.foo" in modules


def test_domain_init_excluded_when_missing(tmp_path) -> None:
    """__init__.py is excluded when it does not exist."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(tmp_path, platforms=[], files=[])
    targets = build_probe_targets(integration, manifest)
    modules = [t.module for t in targets]
    assert "custom_components.foo" not in modules


def test_config_flow_included_when_exists(tmp_path) -> None:
    """config_flow.py is included when it exists."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(
        tmp_path, platforms=[], files=["__init__.py", "config_flow.py"]
    )
    targets = build_probe_targets(integration, manifest)
    modules = [t.module for t in targets]
    assert "custom_components.foo.config_flow" in modules


def test_config_flow_excluded_when_missing(tmp_path) -> None:
    """config_flow.py is excluded when it does not exist."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(
        tmp_path, platforms=[], files=["__init__.py"]
    )
    targets = build_probe_targets(integration, manifest)
    modules = [t.module for t in targets]
    assert "custom_components.foo.config_flow" not in modules


def test_platform_included_when_file_exists(tmp_path) -> None:
    """Platform module is included when its .py file exists."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(
        tmp_path, platforms=["sensor"], files=["__init__.py", "sensor.py"]
    )
    targets = build_probe_targets(integration, manifest)
    modules = [t.module for t in targets]
    assert "custom_components.foo.sensor" in modules


def test_platform_excluded_when_file_missing(tmp_path) -> None:
    """Platform in manifest but missing .py file → NOT included (manifest config drift)."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(
        tmp_path, platforms=["sensor"], files=["__init__.py"]
    )
    targets = build_probe_targets(integration, manifest)
    modules = [t.module for t in targets]
    assert "custom_components.foo.sensor" not in modules


def test_probe_target_file_path_is_absolute(tmp_path) -> None:
    """ProbeTarget.file_path is an absolute path."""
    from hasscheck.smoke.core import build_probe_targets

    integration, manifest = _make_integration(
        tmp_path, platforms=[], files=["__init__.py"]
    )
    targets = build_probe_targets(integration, manifest)
    for t in targets:
        assert t.file_path.is_absolute()
