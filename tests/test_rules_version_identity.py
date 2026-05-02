"""Tests for version identity rules (issue #142 — v0.14.1).

TDD cycle:
  - RED: stubs fail as `pytest.fail("not implemented")`
  - GREEN: confirmed after implementation of each rule

Rules covered:
  - version.identity.present
  - version.manifest.resolvable
  - version.matches.release_tag
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ===========================================================================
# === version.identity.present ===
# ===========================================================================


def _make_ctx(
    root: Path = Path("/tmp/test"),
    integration_path: Path | None = Path("/tmp/test/custom_components/demo"),
    domain: str | None = "demo",
    integration_version: str | None = None,
    integration_version_source: str = "unknown",
    integration_release_tag: str | None = None,
    commit_sha: str | None = None,
) -> object:
    """Helper to build a ProjectContext with version identity fields."""
    from hasscheck.rules.base import ProjectContext

    return ProjectContext(
        root=root,
        integration_path=integration_path,
        domain=domain,
        integration_version=integration_version,
        integration_version_source=integration_version_source,  # type: ignore[arg-type]
        integration_release_tag=integration_release_tag,
        commit_sha=commit_sha,
    )


def test_identity_present_passes_when_version_set() -> None:
    """ctx.integration_version='1.2.3' → PASS."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import version_identity_present_check

    ctx = _make_ctx(integration_version="1.2.3", integration_version_source="manifest")
    finding = version_identity_present_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.PASS


def test_identity_present_warns_when_version_none() -> None:
    """ctx.integration_version=None → WARN with FixSuggestion."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import version_identity_present_check

    ctx = _make_ctx(integration_version=None)
    finding = version_identity_present_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.WARN
    assert finding.fix is not None


def test_identity_present_message_includes_source_when_set() -> None:
    """PASS message contains the source name."""
    from hasscheck.rules.version_identity import version_identity_present_check

    ctx = _make_ctx(integration_version="2.0.0", integration_version_source="git_tag")
    finding = version_identity_present_check(ctx)  # type: ignore[arg-type]
    assert "git_tag" in finding.message


def test_identity_present_finding_uses_version_category() -> None:
    """category == 'version'."""
    from hasscheck.rules.version_identity import version_identity_present_check

    ctx = _make_ctx(integration_version="1.0.0")
    finding = version_identity_present_check(ctx)  # type: ignore[arg-type]
    assert finding.category == "version"


# ===========================================================================
# === version.manifest.resolvable ===
# ===========================================================================


def test_manifest_resolvable_passes_when_source_is_manifest() -> None:
    """source='manifest' → PASS."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import manifest_version_resolvable_check

    ctx = _make_ctx(integration_version="1.0.0", integration_version_source="manifest")
    finding = manifest_version_resolvable_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.PASS


def test_manifest_resolvable_warns_when_source_is_git_tag() -> None:
    """source='git_tag' → WARN (manifest should be canonical)."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import manifest_version_resolvable_check

    ctx = _make_ctx(integration_version="1.0.0", integration_version_source="git_tag")
    finding = manifest_version_resolvable_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.WARN


def test_manifest_resolvable_warns_when_source_is_unknown() -> None:
    """source='unknown' → WARN."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import manifest_version_resolvable_check

    ctx = _make_ctx(integration_version=None, integration_version_source="unknown")
    finding = manifest_version_resolvable_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.WARN


def test_manifest_resolvable_not_applicable_when_no_integration_path() -> None:
    """ctx.integration_path=None → NOT_APPLICABLE."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import manifest_version_resolvable_check

    ctx = _make_ctx(integration_path=None, integration_version_source="unknown")
    finding = manifest_version_resolvable_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.NOT_APPLICABLE


def test_manifest_resolvable_warn_includes_fix_suggestion() -> None:
    """WARN paths carry a FixSuggestion pointing at manifest.json."""
    from hasscheck.rules.version_identity import manifest_version_resolvable_check

    ctx = _make_ctx(integration_version="1.0.0", integration_version_source="git_tag")
    finding = manifest_version_resolvable_check(ctx)  # type: ignore[arg-type]
    assert finding.fix is not None
    assert "manifest" in finding.fix.summary.lower()


# ===========================================================================
# === version.matches.release_tag ===
# ===========================================================================


def _patch_latest_tag(
    monkeypatch: pytest.MonkeyPatch, return_value: str | None
) -> None:
    """Monkeypatch _latest_version_tag to return a fixed value."""
    import hasscheck.rules.version_identity as vi_module

    monkeypatch.setattr(vi_module, "_latest_version_tag", lambda _root: return_value)


def test_matches_release_tag_not_applicable_when_no_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No .git → NOT_APPLICABLE."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, None)
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.0.0",
        integration_version_source="manifest",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.NOT_APPLICABLE


def test_matches_release_tag_not_applicable_when_no_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """git init but no tags → NOT_APPLICABLE."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, None)
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.0.0",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.NOT_APPLICABLE


def test_matches_release_tag_not_applicable_when_no_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tags exist but neither integration_version nor release_tag set → NOT_APPLICABLE."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, "v1.2.3")
    ctx = _make_ctx(
        root=tmp_path,
        integration_version=None,
        integration_release_tag=None,
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.NOT_APPLICABLE


def test_matches_release_tag_passes_when_versions_equal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tag='1.2.3', version='1.2.3' → PASS."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, "1.2.3")
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.2.3",
        integration_version_source="git_tag",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.PASS


def test_matches_release_tag_passes_when_tag_has_v_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tag='v1.2.3', version='1.2.3' → PASS."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, "v1.2.3")
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.2.3",
        integration_version_source="git_tag",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.PASS


def test_matches_release_tag_passes_when_release_tag_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """release_tag='v1.2.3', tag='v1.2.3', version=None → PASS (release_tag wins)."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, "v1.2.3")
    ctx = _make_ctx(
        root=tmp_path,
        integration_version=None,
        integration_release_tag="v1.2.3",
        integration_version_source="github_release",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.PASS


def test_matches_release_tag_fails_when_versions_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tag='1.2.3', version='1.2.4' → FAIL with FixSuggestion."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, "1.2.3")
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.2.4",
        integration_version_source="git_tag",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.FAIL
    assert finding.fix is not None


def test_matches_release_tag_handles_git_subprocess_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """subprocess raises → NOT_APPLICABLE (no crash)."""
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    _patch_latest_tag(monkeypatch, None)
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.0.0",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.NOT_APPLICABLE


def test_matches_release_tag_not_applicable_when_source_not_tag_based(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rule only applies to git_tag / github_release sources.

    Patch _latest_version_tag so git IS present and has a tag, but
    integration_version_source is 'manifest' — rule must return NOT_APPLICABLE
    immediately without comparing versions.
    """
    from hasscheck.models import RuleStatus
    from hasscheck.rules.version_identity import matches_release_tag_check

    # Git is present and has a tag different from the integration version —
    # a spurious WARN would be raised if the source-type guard is missing.
    _patch_latest_tag(monkeypatch, "9.9.9")
    ctx = _make_ctx(
        root=tmp_path,
        integration_version="1.0.0",
        integration_version_source="manifest",
    )
    finding = matches_release_tag_check(ctx)  # type: ignore[arg-type]
    assert finding.status == RuleStatus.NOT_APPLICABLE


# ===========================================================================
# === Registry / wiring ===
# ===========================================================================


def test_version_identity_rules_registered() -> None:
    """All 3 IDs must be present in RULES_BY_ID."""
    from hasscheck.rules.registry import RULES_BY_ID

    assert "version.identity.present" in RULES_BY_ID
    assert "version.manifest.resolvable" in RULES_BY_ID
    assert "version.matches.release_tag" in RULES_BY_ID


def test_version_identity_rules_have_required_fields() -> None:
    """Each RuleDefinition has id/version/category/severity/title/why/source_url/check/overridable."""
    from hasscheck.rules.registry import RULES_BY_ID

    ids = [
        "version.identity.present",
        "version.manifest.resolvable",
        "version.matches.release_tag",
    ]
    for rule_id in ids:
        rule = RULES_BY_ID[rule_id]
        assert rule.id == rule_id
        assert rule.version
        assert rule.category == "version"
        assert rule.severity
        assert rule.title
        assert rule.why
        assert rule.source_url
        assert callable(rule.check)
        assert isinstance(rule.overridable, bool)


def test_version_identity_rules_are_overridable() -> None:
    """overridable=True for all 3."""
    from hasscheck.rules.registry import RULES_BY_ID

    ids = [
        "version.identity.present",
        "version.manifest.resolvable",
        "version.matches.release_tag",
    ]
    for rule_id in ids:
        assert RULES_BY_ID[rule_id].overridable is True, (
            f"{rule_id} must be overridable"
        )


def test_version_identity_rules_use_recommended_severity() -> None:
    """severity=RECOMMENDED for all 3."""
    from hasscheck.models import RuleSeverity
    from hasscheck.rules.registry import RULES_BY_ID

    ids = [
        "version.identity.present",
        "version.manifest.resolvable",
        "version.matches.release_tag",
    ]
    for rule_id in ids:
        assert RULES_BY_ID[rule_id].severity == RuleSeverity.RECOMMENDED, (
            f"{rule_id} must use RECOMMENDED severity"
        )
