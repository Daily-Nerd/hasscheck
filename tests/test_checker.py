import json

import pytest

from hasscheck.checker import run_check
from hasscheck.config import HassCheckConfig, RuleOverride
from hasscheck.models import RuleStatus


def test_missing_custom_components_and_manifest_are_reported(tmp_path) -> None:
    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["hacs.custom_components.exists"].status is RuleStatus.FAIL
    assert findings["manifest.exists"].status is RuleStatus.FAIL
    assert findings["manifest.domain.exists"].status is RuleStatus.NOT_APPLICABLE


def test_manifest_domain_passes_for_custom_integration(tmp_path) -> None:
    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "demo",
                "name": "Demo",
                "documentation": "https://example.com",
                "issue_tracker": "https://example.com/issues",
                "codeowners": ["@demo"],
                "version": "0.1.0",
            }
        ),
        encoding="utf-8",
    )

    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["hacs.custom_components.exists"].status is RuleStatus.PASS
    assert findings["manifest.exists"].status is RuleStatus.PASS
    assert findings["manifest.domain.exists"].status is RuleStatus.PASS


# ---------- Phase 4: config kwarg + discovery ----------


def test_run_check_config_and_no_config_conflict(tmp_path) -> None:
    with pytest.raises(ValueError, match="no_config"):
        run_check(tmp_path, config=HassCheckConfig(), no_config=True)


def test_run_check_no_config_flag_skips_yaml(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — a real override target
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    report = run_check(tmp_path, no_config=True)
    assert report.summary.overrides_applied.count == 0


def test_run_check_discovers_yaml_at_root(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — confirms the override is actually applied
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    report = run_check(tmp_path)
    assert report.summary.overrides_applied.count == 1
    assert "tests.folder.exists" in report.summary.overrides_applied.rule_ids


def test_run_check_applies_overrides_from_config_kwarg(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — confirms source="config" is set
    config = HassCheckConfig(
        rules={
            "tests.folder.exists": RuleOverride(status="not_applicable", reason="test")
        }
    )
    report = run_check(tmp_path, config=config)
    findings = {f.rule_id: f for f in report.findings}
    assert findings["tests.folder.exists"].status is RuleStatus.NOT_APPLICABLE
    assert findings["tests.folder.exists"].applicability.source == "config"
    assert report.summary.overrides_applied.count == 1


def test_run_check_no_yaml_overrides_applied_is_empty(tmp_path) -> None:
    report = run_check(tmp_path)
    assert report.summary.overrides_applied.count == 0
    assert report.summary.overrides_applied.rule_ids == []


def test_run_check_schema_version_is_0_5_0(tmp_path) -> None:
    report = run_check(tmp_path)
    assert report.schema_version == "0.5.0"


# ---------- v0.8: Ruleset ID bump ----------


def test_default_ruleset_id_is_hasscheck_ha_2026_5() -> None:
    from hasscheck.models import DEFAULT_RULESET_ID

    assert DEFAULT_RULESET_ID == "hasscheck-ha-2026.5"


# ---------- v0.13: Provenance block (#130) ----------


def test_run_check_report_provenance_key_present(tmp_path) -> None:
    """Round-trip: run_check → to_json_dict → parse → 'provenance' key present."""
    import json

    report = run_check(tmp_path)
    raw = report.to_json_dict()
    reparsed = json.loads(json.dumps(raw))

    assert "provenance" in reparsed
    assert reparsed["schema_version"] == "0.5.0"


def test_run_check_report_provenance_is_not_none(tmp_path) -> None:
    """run_check() populates provenance on the returned report."""
    report = run_check(tmp_path)
    assert report.provenance is not None


# ---------- Phase 3 — Checker SSoT + ProjectContext wiring ----------


def test_checker_calls_read_manifest_version_only_once(monkeypatch, tmp_path) -> None:
    """Spy on target.read_manifest_version; assert called <= 1 per run_check."""
    import hasscheck.target as target_module

    call_count = 0
    original = target_module.read_manifest_version

    def spy(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(target_module, "read_manifest_version", spy)

    import json

    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo", "name": "Demo", "version": "1.0.0"})
    )

    run_check(tmp_path)
    assert call_count <= 1, (
        f"read_manifest_version called {call_count} times (expected <= 1)"
    )


def test_checker_populates_version_identity_into_context(tmp_path) -> None:
    """Run check on a tmp integration path; findings must include 'version' category."""
    import json

    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo", "name": "Demo", "version": "1.0.0"})
    )

    report = run_check(tmp_path)
    version_findings = [f for f in report.findings if f.category == "version"]
    assert len(version_findings) > 0, (
        "Expected at least one finding with category='version' after context wiring"
    )


def test_category_label_version_identity_present() -> None:
    """CATEGORY_LABELS['version'] must equal 'Version Identity'."""
    from hasscheck.checker import CATEGORY_LABELS

    assert CATEGORY_LABELS["version"] == "Version Identity"
