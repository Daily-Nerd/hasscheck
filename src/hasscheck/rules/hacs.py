"""HACS installability rules — 9 rules under the hacs.* namespace.

These rules cover HACS installability semantics beyond the structural-presence
checks in hacs_structure.py. Three rules require GitHub API access and return
NOT_APPLICABLE in static-check mode; six rules operate on the filesystem only.

Design: sdd/145-hacs-rules/design (D1–D8)
Issue: #145
ADR: docs/decisions/0020-hacs-installability-rules.md
"""

from __future__ import annotations

import json

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.rules.base import ProjectContext, RuleDefinition

HACS_SOURCE = "https://www.hacs.xyz/docs/publish/integration/"

# Known top-level keys for hacs.json v1 (ADR 0020 D5 — 11 keys).
_HACS_KNOWN_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "content_in_root",
        "zip_release",
        "filename",
        "hide_default_branch",
        "homeassistant",
        "hacs",
        "render_readme",
        "country",
        "iot_class",
        "domains",
    }
)


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _read_hacs_json(context: ProjectContext) -> dict | None:
    """Read and parse hacs.json from the project root.

    Returns the parsed dict on success, or None when the file is absent,
    contains invalid JSON, or has a non-dict root value. Never raises.
    """
    path = context.root / "hacs.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


# ---------------------------------------------------------------------------
# Rule: hacs.hacs_json_schema_valid
# ---------------------------------------------------------------------------


def check_hacs_json_schema_valid(context: ProjectContext) -> Finding:
    """Validate hacs.json schema — known keys + required 'name' field.

    - hacs.json absent → PASS (HACS uses defaults)
    - Invalid JSON → FAIL
    - Unknown key → FAIL
    - No 'name' key → FAIL
    - Valid schema with 'name' → PASS
    """
    path = context.root / "hacs.json"
    _rule_id = "hacs.hacs_json_schema_valid"
    _rule_version = "0.15.6"
    _category = "hacs_structure"
    _severity = RuleSeverity.REQUIRED
    _title = "hacs.json schema is valid"

    if not path.is_file():
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.PASS,
            severity=_severity,
            title=_title,
            message="hacs.json is absent; HACS uses built-in defaults.",
            applicability=Applicability(
                reason="hacs.json is optional; HACS applies defaults when absent."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=None,
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message=f"hacs.json is not valid JSON: {exc.msg}.",
            applicability=Applicability(
                reason="hacs.json must be valid JSON for HACS to read it."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path="hacs.json",
        )

    if not isinstance(payload, dict):
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message="hacs.json root must be a JSON object, not an array or scalar.",
            applicability=Applicability(
                reason="HACS expects hacs.json to be a top-level JSON object."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path="hacs.json",
        )

    unknown_keys = set(payload) - _HACS_KNOWN_KEYS
    if unknown_keys:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message=(
                f"hacs.json contains unknown key(s): "
                f"{', '.join(sorted(unknown_keys))}. "
                f"Known v1 keys: {', '.join(sorted(_HACS_KNOWN_KEYS))}."
            ),
            applicability=Applicability(
                reason="Unknown keys are not recognised by HACS and may cause errors."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path="hacs.json",
        )

    if "name" not in payload:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message="hacs.json is missing the required 'name' key.",
            applicability=Applicability(
                reason="HACS requires the 'name' field in hacs.json."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path="hacs.json",
        )

    return Finding(
        rule_id=_rule_id,
        rule_version=_rule_version,
        category=_category,
        status=RuleStatus.PASS,
        severity=_severity,
        title=_title,
        message="hacs.json schema is valid.",
        applicability=Applicability(
            reason="hacs.json is present, valid JSON, all keys known, and 'name' is present."
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path="hacs.json",
    )


# ---------------------------------------------------------------------------
# Rule: hacs.one_integration_per_repo
# ---------------------------------------------------------------------------


def check_one_integration_per_repo(context: ProjectContext) -> Finding:
    """Check that custom_components/ contains exactly one integration.

    Count subdirectories under custom_components/ that contain manifest.json.
    - Count > 1 → FAIL
    - Count == 1 → PASS
    - Count == 0 or custom_components/ absent → PASS
    """
    _rule_id = "hacs.one_integration_per_repo"
    _rule_version = "0.15.6"
    _category = "hacs_structure"
    _severity = RuleSeverity.REQUIRED
    _title = "Repository contains exactly one integration"

    cc_path = context.root / "custom_components"
    if not cc_path.is_dir():
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.PASS,
            severity=_severity,
            title=_title,
            message="No custom_components/ directory found; layout rule handles this.",
            applicability=Applicability(
                reason="HACS requires exactly one integration per repository."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=None,
        )

    integrations = [
        d for d in cc_path.iterdir() if d.is_dir() and (d / "manifest.json").is_file()
    ]

    if len(integrations) > 1:
        names = ", ".join(sorted(d.name for d in integrations))
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message=(
                f"Found {len(integrations)} integrations in custom_components/: {names}. "
                f"HACS supports only one integration per repository."
            ),
            applicability=Applicability(
                reason="HACS requires exactly one integration per repository."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path="custom_components",
        )

    return Finding(
        rule_id=_rule_id,
        rule_version=_rule_version,
        category=_category,
        status=RuleStatus.PASS,
        severity=_severity,
        title=_title,
        message="Repository contains exactly one integration in custom_components/.",
        applicability=Applicability(
            reason="HACS requires exactly one integration per repository."
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.info_or_readme_present
# ---------------------------------------------------------------------------


def check_info_or_readme_present(context: ProjectContext) -> Finding:
    """Check that info.md or README.md exists at root and is non-empty (case-insensitive).

    - At least one file exists AND has size > 0 → PASS
    - Both absent → FAIL
    - Only empty files → FAIL
    """
    _rule_id = "hacs.info_or_readme_present"
    _rule_version = "0.15.6"
    _category = "hacs_structure"
    _severity = RuleSeverity.RECOMMENDED
    _title = "info.md or README.md is present and non-empty"

    candidates = []
    for child in context.root.iterdir():
        if child.is_file() and child.name.lower() in ("info.md", "readme.md"):
            candidates.append(child)

    non_empty = [f for f in candidates if f.stat().st_size > 0]

    if non_empty:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.PASS,
            severity=_severity,
            title=_title,
            message=f"Found non-empty documentation file: {non_empty[0].name}.",
            applicability=Applicability(
                reason="HACS requires a human-readable description for the integration."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=non_empty[0].name,
        )

    if candidates:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message="info.md / README.md exists but is empty (0 bytes).",
            applicability=Applicability(
                reason="HACS requires a non-empty human-readable description."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=candidates[0].name,
        )

    return Finding(
        rule_id=_rule_id,
        rule_version=_rule_version,
        category=_category,
        status=RuleStatus.FAIL,
        severity=_severity,
        title=_title,
        message="Neither info.md nor README.md (case-insensitive) found at repository root.",
        applicability=Applicability(
            reason="HACS requires a human-readable description for the integration."
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.download_strategy_clear
# ---------------------------------------------------------------------------


def check_download_strategy_clear(context: ProjectContext) -> Finding:
    """Check that content_in_root and zip_release are not both set to true.

    - Both true → FAIL
    - Any other combination (including absent hacs.json) → PASS
    """
    _rule_id = "hacs.download_strategy_clear"
    _rule_version = "0.15.6"
    _category = "hacs_structure"
    _severity = RuleSeverity.RECOMMENDED
    _title = "Download strategy is unambiguous"

    data = _read_hacs_json(context)

    if data is not None:
        content_in_root = bool(data.get("content_in_root", False))
        zip_release = bool(data.get("zip_release", False))

        if content_in_root and zip_release:
            return Finding(
                rule_id=_rule_id,
                rule_version=_rule_version,
                category=_category,
                status=RuleStatus.FAIL,
                severity=_severity,
                title=_title,
                message=(
                    "Both 'content_in_root' and 'zip_release' are true in hacs.json. "
                    "Only one download strategy can be active at a time."
                ),
                applicability=Applicability(
                    reason="Conflicting download strategies prevent HACS from installing correctly."
                ),
                source=RuleSource(url=HACS_SOURCE),
                fix=None,
                path="hacs.json",
            )

    return Finding(
        rule_id=_rule_id,
        rule_version=_rule_version,
        category=_category,
        status=RuleStatus.PASS,
        severity=_severity,
        title=_title,
        message="Download strategy is unambiguous.",
        applicability=Applicability(
            reason="Exactly one download strategy is active (or HACS uses the default)."
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.content_in_root_consistent
# ---------------------------------------------------------------------------


def check_content_in_root_consistent(context: ProjectContext) -> Finding:
    """Check that content_in_root flag is consistent with the repo layout.

    - hacs.json absent or unparseable → NOT_APPLICABLE
    - content_in_root: true AND custom_components/ present → FAIL
    - content_in_root: true AND no custom_components/ → PASS
    - content_in_root: false/absent AND custom_components/ present → PASS
    - content_in_root: false/absent AND no custom_components/ → FAIL
    """
    _rule_id = "hacs.content_in_root_consistent"
    _rule_version = "0.15.6"
    _category = "hacs_structure"
    _severity = RuleSeverity.RECOMMENDED
    _title = "content_in_root flag is consistent with repository layout"

    data = _read_hacs_json(context)

    if data is None:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.NOT_APPLICABLE,
            severity=_severity,
            title=_title,
            message="hacs.json absent or unparseable; cannot evaluate content_in_root.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="content_in_root requires a readable hacs.json.",
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=None,
        )

    content_in_root = bool(data.get("content_in_root", False))
    cc_exists = (context.root / "custom_components").is_dir()

    if content_in_root:
        if cc_exists:
            return Finding(
                rule_id=_rule_id,
                rule_version=_rule_version,
                category=_category,
                status=RuleStatus.FAIL,
                severity=_severity,
                title=_title,
                message=(
                    "hacs.json sets content_in_root: true, but custom_components/ "
                    "exists at the repository root. Remove custom_components/ or "
                    "set content_in_root: false."
                ),
                applicability=Applicability(
                    reason="content_in_root: true means integration files are in the root, not custom_components/."
                ),
                source=RuleSource(url=HACS_SOURCE),
                fix=None,
                path="hacs.json",
            )
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.PASS,
            severity=_severity,
            title=_title,
            message="content_in_root: true and no custom_components/ directory — layout is consistent.",
            applicability=Applicability(
                reason="Integration files reside at the repository root as declared."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=None,
        )

    # content_in_root is false or absent — expect custom_components/ to exist
    if cc_exists:
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.PASS,
            severity=_severity,
            title=_title,
            message="content_in_root not set (defaults to false) and custom_components/ exists — layout is consistent.",
            applicability=Applicability(
                reason="Standard HACS integration layout uses custom_components/."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=None,
        )

    return Finding(
        rule_id=_rule_id,
        rule_version=_rule_version,
        category=_category,
        status=RuleStatus.FAIL,
        severity=_severity,
        title=_title,
        message=(
            "content_in_root is false (or absent) but custom_components/ does not exist. "
            "HACS cannot find the integration files."
        ),
        applicability=Applicability(
            reason="Standard HACS integration layout expects custom_components/<domain>/."
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.default_branch_installable
# ---------------------------------------------------------------------------


def check_default_branch_installable(context: ProjectContext) -> Finding:
    """Check that the integration path contains a manifest.json.

    - integration_path resolves to a dir with manifest.json → PASS
    - manifest.json absent or integration_path is None → FAIL
    """
    _rule_id = "hacs.default_branch_installable"
    _rule_version = "0.15.6"
    _category = "hacs_structure"
    _severity = RuleSeverity.RECOMMENDED
    _title = "Default branch is installable by HACS"

    if context.integration_path is None or not context.integration_path.is_dir():
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message="Integration directory not found; HACS cannot install from the default branch.",
            applicability=Applicability(
                reason="HACS installs from the integration directory on the default branch."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=None,
        )

    manifest_path = context.integration_path / "manifest.json"
    if not manifest_path.is_file():
        return Finding(
            rule_id=_rule_id,
            rule_version=_rule_version,
            category=_category,
            status=RuleStatus.FAIL,
            severity=_severity,
            title=_title,
            message=(
                f"manifest.json not found in {context.integration_path.name}/. "
                f"HACS requires manifest.json to validate and install the integration."
            ),
            applicability=Applicability(
                reason="HACS reads manifest.json to validate the integration before installation."
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=None,
            path=str(context.integration_path / "manifest.json"),
        )

    return Finding(
        rule_id=_rule_id,
        rule_version=_rule_version,
        category=_category,
        status=RuleStatus.PASS,
        severity=_severity,
        title=_title,
        message="Integration directory contains manifest.json; default branch is installable.",
        applicability=Applicability(
            reason="HACS can install from the default branch when manifest.json is present."
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.release_zip_valid (GH-API — NOT_APPLICABLE in static mode)
# ---------------------------------------------------------------------------


def check_release_zip_valid(context: ProjectContext) -> Finding:
    """Always NOT_APPLICABLE — requires GitHub Releases API (deferred to hub)."""
    return Finding(
        rule_id="hacs.release_zip_valid",
        rule_version="0.15.6",
        category="hacs_structure",
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title="Release ZIP is valid",
        message="GitHub API not available in static check mode — enriched on hub.",
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason="Requires GitHub Releases API; deferred to hub enrichment.",
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.github_release_assets_valid (GH-API — NOT_APPLICABLE in static mode)
# ---------------------------------------------------------------------------


def check_github_release_assets_valid(context: ProjectContext) -> Finding:
    """Always NOT_APPLICABLE — requires GitHub Releases API (deferred to hub)."""
    return Finding(
        rule_id="hacs.github_release_assets_valid",
        rule_version="0.15.6",
        category="hacs_structure",
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title="GitHub release assets are valid",
        message="GitHub API not available in static check mode — enriched on hub.",
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason="Requires GitHub Releases API; deferred to hub enrichment.",
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule: hacs.repository_topics_present (GH-API — NOT_APPLICABLE in static mode)
# ---------------------------------------------------------------------------


def check_repository_topics_present(context: ProjectContext) -> Finding:
    """Always NOT_APPLICABLE — requires GitHub Topics API (deferred to hub)."""
    return Finding(
        rule_id="hacs.repository_topics_present",
        rule_version="0.15.6",
        category="hacs_structure",
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title="Repository topics are present",
        message="GitHub API not available in static check mode — enriched on hub.",
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason="Requires GitHub Topics API; deferred to hub enrichment.",
        ),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path=None,
    )


# ---------------------------------------------------------------------------
# Rule catalog (exported)
# ---------------------------------------------------------------------------

RULES: list[RuleDefinition] = [
    RuleDefinition(
        id="hacs.hacs_json_schema_valid",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.REQUIRED,
        title="hacs.json schema is valid",
        why=(
            "hacs.json must contain only known v1 keys and the required 'name' field "
            "so that HACS can parse and validate the repository metadata."
        ),
        source_url=HACS_SOURCE,
        check=check_hacs_json_schema_valid,
        overridable=False,
    ),
    RuleDefinition(
        id="hacs.one_integration_per_repo",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.REQUIRED,
        title="Repository contains exactly one integration",
        why=(
            "HACS supports one integration per repository. Multiple integrations "
            "under custom_components/ confuse HACS installers and the hub."
        ),
        source_url=HACS_SOURCE,
        check=check_one_integration_per_repo,
        overridable=False,
    ),
    RuleDefinition(
        id="hacs.info_or_readme_present",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="info.md or README.md is present and non-empty",
        why=(
            "HACS displays info.md (preferred) or README.md on the integration's "
            "page in the HACS store. A missing or empty file degrades the user experience."
        ),
        source_url=HACS_SOURCE,
        check=check_info_or_readme_present,
        overridable=True,
    ),
    RuleDefinition(
        id="hacs.download_strategy_clear",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="Download strategy is unambiguous",
        why=(
            "Enabling both content_in_root and zip_release simultaneously is "
            "contradictory and will cause HACS to fail or behave unpredictably."
        ),
        source_url=HACS_SOURCE,
        check=check_download_strategy_clear,
        overridable=True,
    ),
    RuleDefinition(
        id="hacs.content_in_root_consistent",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="content_in_root flag is consistent with repository layout",
        why=(
            "When content_in_root is true, HACS expects integration files at the "
            "repository root, not inside custom_components/. A mismatch causes "
            "installation failures."
        ),
        source_url=HACS_SOURCE,
        check=check_content_in_root_consistent,
        overridable=True,
    ),
    RuleDefinition(
        id="hacs.default_branch_installable",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="Default branch is installable by HACS",
        why=(
            "HACS installs integrations directly from the default branch when no "
            "release is available. A missing manifest.json prevents installation."
        ),
        source_url=HACS_SOURCE,
        check=check_default_branch_installable,
        overridable=True,
    ),
    RuleDefinition(
        id="hacs.release_zip_valid",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="Release ZIP is valid",
        why=(
            "HACS zip_release integrations are installed from a GitHub Release ZIP. "
            "An invalid or missing ZIP causes installation to fail silently."
        ),
        source_url=HACS_SOURCE,
        check=check_release_zip_valid,
        overridable=True,
    ),
    RuleDefinition(
        id="hacs.github_release_assets_valid",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="GitHub release assets are valid",
        why=(
            "HACS validates release assets when zip_release is true. Invalid or "
            "missing assets cause installation failures for end users."
        ),
        source_url=HACS_SOURCE,
        check=check_github_release_assets_valid,
        overridable=True,
    ),
    RuleDefinition(
        id="hacs.repository_topics_present",
        version="0.15.6",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="Repository topics are present",
        why=(
            "HACS uses GitHub repository topics for categorisation and discoverability "
            "in the HACS store. Missing topics reduce visibility."
        ),
        source_url=HACS_SOURCE,
        check=check_repository_topics_present,
        overridable=True,
    ),
]
