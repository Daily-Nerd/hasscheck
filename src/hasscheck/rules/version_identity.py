"""Version identity rules — version.identity.present, version.manifest.resolvable,
version.matches.release_tag.

These rules read pre-resolved version identity fields off ProjectContext (populated
in checker.py from detect_target's ReportTarget). The matches-release-tag rule
also calls _latest_version_tag(root) to compare against the most recent git tag.

Issue #142 — v0.14.1.
"""

from __future__ import annotations

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    FixSuggestion,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.rules.base import ProjectContext, RuleDefinition
from hasscheck.target import _latest_version_tag

CATEGORY = "version"
_DEV_DOCS_URL = (
    "https://developers.home-assistant.io/docs/creating_integration_manifest#version"
)
_SOURCE_CHECKED_AT = "2026-05-01"
_SOURCE = RuleSource(url=_DEV_DOCS_URL, checked_at=_SOURCE_CHECKED_AT)


# ---------------------------------------------------------------------------
# Rule: version.identity.present
# ---------------------------------------------------------------------------

_PRESENT_RULE_ID = "version.identity.present"
_PRESENT_TITLE = "Integration declares a version identity"


def version_identity_present_check(context: ProjectContext) -> Finding:
    has_version = context.integration_version is not None
    return Finding(
        rule_id=_PRESENT_RULE_ID,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if has_version else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title=_PRESENT_TITLE,
        message=(
            f"Integration version detected: {context.integration_version!r} "
            f"(source: {context.integration_version_source})."
            if has_version
            else "No integration version could be detected from manifest, "
            "git tags, or GITHUB_REF."
        ),
        applicability=Applicability(
            reason="A discoverable version identity is needed for reporting and reproducibility."
        ),
        source=_SOURCE,
        fix=None
        if has_version
        else FixSuggestion(
            summary='Add a "version" field to manifest.json or tag the release with git.',
            docs_url=_DEV_DOCS_URL,
        ),
    )


# ---------------------------------------------------------------------------
# Rule: version.manifest.resolvable
# ---------------------------------------------------------------------------

_MANIFEST_RULE_ID = "version.manifest.resolvable"
_MANIFEST_TITLE = "Version is resolvable from manifest.json"


def manifest_version_resolvable_check(context: ProjectContext) -> Finding:
    source = context.integration_version_source
    is_manifest = source == "manifest"
    if context.integration_path is None:
        return Finding(
            rule_id=_MANIFEST_RULE_ID,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=_MANIFEST_TITLE,
            message="No integration path detected — cannot inspect manifest.json.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="No integration_path on context.",
            ),
            source=_SOURCE,
        )
    return Finding(
        rule_id=_MANIFEST_RULE_ID,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if is_manifest else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title=_MANIFEST_TITLE,
        message=(
            f"manifest.json declares version {context.integration_version!r}."
            if is_manifest
            else f"Version source is {source!r}, not 'manifest'. "
            "manifest.json should declare a 'version' field for reproducibility."
        ),
        applicability=Applicability(
            reason="manifest.json is the canonical source of integration version."
        ),
        source=_SOURCE,
        fix=None
        if is_manifest
        else FixSuggestion(
            summary='Add or fix the "version" field in manifest.json.',
            docs_url=_DEV_DOCS_URL,
        ),
    )


# ---------------------------------------------------------------------------
# Rule: version.matches.release_tag
# ---------------------------------------------------------------------------

_TAG_RULE_ID = "version.matches.release_tag"
_TAG_TITLE = "Manifest version matches the latest git release tag"


def matches_release_tag_check(context: ProjectContext) -> Finding:
    # Source-type guard: rule only applies when the version is sourced from a
    # git tag or GitHub release. Any other source (e.g. "manifest", "unknown")
    # means comparing against the latest git tag is meaningless.
    if context.integration_version_source not in {"git_tag", "github_release"}:
        return Finding(
            rule_id=_TAG_RULE_ID,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=_TAG_TITLE,
            message=(
                f"Version source is {context.integration_version_source!r}; "
                "rule only applies to git_tag and github_release."
            ),
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="Version source is not tag-based.",
            ),
            source=_SOURCE,
        )

    latest_tag = _latest_version_tag(context.root)
    manifest_version = context.integration_version
    release_tag = context.integration_release_tag

    # No git or no tags → not applicable
    if latest_tag is None:
        return Finding(
            rule_id=_TAG_RULE_ID,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=_TAG_TITLE,
            message="No git tags found (or not a git checkout) — cannot compare.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="No latest git tag available.",
            ),
            source=_SOURCE,
        )

    # Determine the comparison value: prefer release_tag (CI), fall back to manifest_version
    candidate = release_tag or manifest_version
    if candidate is None:
        return Finding(
            rule_id=_TAG_RULE_ID,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=_TAG_TITLE,
            message=f"Latest git tag is {latest_tag!r} but no manifest version "
            "or release tag detected — cannot compare.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="No version candidate to compare with git tag.",
            ),
            source=_SOURCE,
        )

    matches = _versions_align(candidate, latest_tag)
    return Finding(
        rule_id=_TAG_RULE_ID,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if matches else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title=_TAG_TITLE,
        message=(
            f"Version {candidate!r} aligns with latest git tag {latest_tag!r}."
            if matches
            else f"Version {candidate!r} does not match latest git tag {latest_tag!r}."
        ),
        applicability=Applicability(
            reason="Aligned manifest and tag versions confirm the release identity."
        ),
        source=_SOURCE,
        fix=None
        if matches
        else FixSuggestion(
            summary="Bump manifest.json version OR create a matching git tag for this release.",
            docs_url=_DEV_DOCS_URL,
        ),
    )


def _versions_align(version: str, tag: str) -> bool:
    """Return True if ``version`` matches ``tag`` (with optional 'v' prefix on tag)."""
    return version == tag or tag == f"v{version}" or version == tag.lstrip("v")


# ---------------------------------------------------------------------------
# Rule registry export
# ---------------------------------------------------------------------------

RULES = [
    RuleDefinition(
        id=_PRESENT_RULE_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_PRESENT_TITLE,
        why="A discoverable version identity is needed for reporting, caching, and reproducibility of hasscheck findings.",
        source_url=_DEV_DOCS_URL,
        check=version_identity_present_check,
        overridable=True,
    ),
    RuleDefinition(
        id=_MANIFEST_RULE_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_MANIFEST_TITLE,
        why="manifest.json is the canonical, in-tree source of integration version. Tag-only versioning is fragile across distribution channels.",
        source_url=_DEV_DOCS_URL,
        check=manifest_version_resolvable_check,
        overridable=True,
    ),
    RuleDefinition(
        id=_TAG_RULE_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_TAG_TITLE,
        why="When a git tag and a manifest version disagree, downstream consumers cannot reliably identify which build is being checked.",
        source_url=_DEV_DOCS_URL,
        check=matches_release_tag_check,
        overridable=True,
    ),
]
