# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `LICENSE` — MIT License at repository root, "Copyright (c) 2026 Daily Nerd"
- `pyproject.toml` PyPI-grade metadata: `license = "MIT"` (SPDX/PEP 639), `authors`, `keywords`, `classifiers`, and `[project.urls]` (Homepage, Repository, Issues, Documentation)
- ADR 0009 — Schema versioning policy: documents `SCHEMA_VERSION` bump triggers, additive-only stance, lockstep with `hasscheck-web`, and distinction from ADR 0006's ruleset versioning (policy-only; no version bump)

### Changed
- README "Current status" block reflects v0.7.0 as latest release and v0.8.0 as in-progress
- README GitHub Action examples bumped from `@v0.6.0` to `@v0.7.0` (lines 69 and 109)

## [0.7.0] — 2026-05-01

### Added
- ADR 0008 — hosted reports publish contract (two-repo split, GitHub OIDC auth, schema lockstep, last-50 retention, free-for-all v0.7, monetization constraints)
- `docs/architecture/publish-handshake.md` — client-side OIDC flow, request/response shapes, error semantics, withdrawal commands
- `docs/README.md` refreshed: project status table through v0.7, links to all architecture docs and ADRs 0001-0008, OSS/proprietary split note
- `CHANGELOG.md` — Keep a Changelog 1.1.0 format, populated retroactively from v0.1.0 through v0.7.0
- `src/hasscheck/slug.py` — best-effort `owner/repo` detection from git remote with manifest `issue_tracker` fallback
- `ProjectInfo.repo_slug: str | None` field on the JSON report (additive per ADR 0006)
- `hasscheck publish` CLI command — opt-in upload to a hosted service via GitHub OIDC. Supports `--withdraw --report-id <id>` and `--withdraw-all`. Endpoint and token resolution: CLI flag > env var (`HASSCHECK_PUBLISH_ENDPOINT`, `HASSCHECK_OIDC_TOKEN`) > default (`https://hasscheck.io`).
- `httpx>=0.27` runtime dependency (publish client only)
- `hasscheck init` CLI command — bootstraps a repo with `hasscheck.yaml` and `.github/workflows/hasscheck.yml`. Supports `--dry-run`, `--force`, `--skip-action`. Refuses to overwrite existing files unless `--force`.
- `src/hasscheck/scaffold/templates/hasscheck.yaml.tmpl` — conservative `hasscheck.yaml` template used by `init`
- `emit-publish` and `publish-endpoint` inputs on the composite GitHub Action. When `emit-publish: 'true'`, the action requests a workflow OIDC token (audience `hasscheck-web`) and runs `hasscheck publish`. Requires workflow-level `permissions: id-token: write`.

### Changed
- Bumped `version` and `__version__` to `0.7.0`
- README "Current status" reflects v0.6.0 latest + v0.7.0 in-planning at the time of writing; refreshed during the release
- Action example versions bumped to v0.6.0 across README sections during the docs refresh
- "Non-goals for v0.4.0" → "Non-goals" (stale version dropped)
- Dropped "/bad" claim from fixture description (no tracked files yet; tracked separately)

[Compare v0.6.0...v0.7.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.6.0...v0.7.0)

## [0.6.0] — 2026-05-01

### Added
- `hasscheck badge` CLI command — opt-in shields.io endpoint JSON generator, per-category quality signal artifacts and an umbrella `hasscheck.json`
- `emit-badges` input on the composite GitHub Action — uploads a `hasscheck-badges` artifact when set to `'true'`
- `BADGE_MANIFEST_SCHEMA_VERSION` constant + `manifest.json` artifact index
- Runtime forbidden-language guard (`assert_label_is_clean`) and property test enforcing the blocklist on every release
- ADR 0007 — Badge policy: opt-in only, forbidden language, layered-status contract
- `docs/architecture/badges.md` — badge architecture, status mapping, GitHub Pages recipe
- README "Badges (opt-in)" section with embedding instructions
- Registry guard: `RULES_BY_ID` raises on duplicate rule IDs at import time (#31)
- `detect.py` warning when multiple integrations are found under `custom_components/` (#30)
- ADR 0006 — Ruleset versioning policy (`DEFAULT_RULESET_ID` + `DEFAULT_SOURCE_CHECKED_AT` bump rules) (#32)

### Changed
- `hasscheck schema` docstring corrected from "v0.1 JSON schema" to current schema (#29)
- `ToolInfo.version` now sourced from `__version__` instead of hardcoded literal (#28)

[Compare v0.5.0...v0.6.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.5.0...v0.6.0)

## [0.5.0] — 2026-05-01

### Added
- Composite GitHub Action (`Daily-Nerd/hasscheck@v0.5.0`) — runs `hasscheck check`, uploads JSON artifact, optional PR comment with markdown report (#39)
- Markdown report renderer (`report_to_md`) (#38)
- Unified `--format {terminal,json,md}` flag on `hasscheck check`, replacing `--json` (#37)

### Fixed
- `detect.py` no longer silently picks the first integration when multiple are present — emits a warning naming the chosen one (#30)
- Test suite no longer hardcodes the version string in `test_pyproject_version_matches_tool_info`

[Compare v0.4.0...v0.5.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.4.0...v0.5.0)

## [0.4.0] — 2026-05-01

### Added
- Scaffolding subcommand group (`hasscheck scaffold`) with `--dry-run` and `--force` (#19)
- `scaffold github-action` — generates `.github/workflows/hasscheck.yml` (#22)
- `scaffold diagnostics` — generates `<integration>/diagnostics.py` with redaction helpers; gated on `supports_diagnostics: true` (#23)
- `scaffold repairs` — generates `<integration>/repairs.py` with `ConfirmRepairFlow` skeleton; gated on `has_user_fixable_repairs: true` (#24)
- `string.Template`-based scaffold engine + `templates/` static `.tmpl` files
- ADR 0005 — Scaffolding policy
- `docs/architecture/scaffolding.md`
- Fix-suggestion rendering in terminal output

[Compare v0.3.0...v0.4.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.3.0...v0.4.0)

## [0.3.0] — 2026-05-01

### Added
- Project applicability context — `applicability:` block in `hasscheck.yaml`
- `ProjectApplicability` model with `supports_diagnostics`, `has_user_fixable_repairs`, `uses_config_flow` flags
- `ApplicabilityApplied` summary metadata on the JSON report
- ADR 0004 — Project applicability context
- `docs/architecture/project-applicability-context.md`

### Changed
- Rules consume project applicability facts to return `not_applicable` instead of generic `warn`/`fail`

[Compare v0.2.1...v0.3.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.2.1...v0.3.0)

## [0.2.1] — 2026-05-01

### Fixed
- `__version__` and `ToolInfo.version` aligned with `pyproject.toml` (drift from 0.2.0 release detected; bumped to 0.2.1 to correct)

[Compare v0.2.0...v0.2.1](https://github.com/Daily-Nerd/hasscheck/compare/v0.2.0...v0.2.1)

## [0.2.0] — 2026-05-01

### Added
- `hasscheck.yaml` config file support — per-rule overrides
- `RuleOverride` model with `status` ∈ {`not_applicable`, `manual_review`} and required `reason`
- `apply_overrides()` engine: locked vs softenable rules; never elevates fail→pass
- Override warnings to stderr for stale/redundant/unknown overrides
- `ConfigError` raised on locked-rule override or malformed YAML
- `--no-config` CLI flag to ignore `hasscheck.yaml` (CI debugging)
- Overrides banner in terminal report + `(config)` marker on overridden findings
- Overridable line on `hasscheck explain`
- ADR 0001 — Config override policy
- ADR 0002 — Block A deferred to v0.3
- ADR 0003 — Config-file override policy
- `docs/architecture/config-file.md`
- `hasscheck.example.yaml` annotated example
- `OverridesApplied` summary metadata on the JSON report

[Compare v0.1.0...v0.2.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.1.0...v0.2.0)

## [0.1.0] — 2026-05-01

### Added
- Initial public release: local CLI for Home Assistant custom integration quality signals
- Typer CLI with `check`, `schema`, `explain` commands
- Pydantic JSON report schema (`HassCheckReport`) with `pass`/`warn`/`fail`/`not_applicable`/`manual_review` statuses
- Rule IDs, rule versions, ruleset metadata, source URLs, and `source_checked_at` timestamps
- Rich terminal output with category summaries
- Rule packs: HACS structure, brand assets, manifest metadata, config flow, diagnostics, repairs, docs, repository, tests, CI
- Project detection (`custom_components/<domain>/`)
- Example `good_integration` and `partial_integration` fixtures
- Pytest coverage for the v0.1 rule set
- Unofficial disclaimer everywhere — no certification, safety, or HACS-acceptance language

[Initial release](https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.1.0)

[Unreleased]: https://github.com/Daily-Nerd/hasscheck/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.7.0
[0.6.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.6.0
[0.5.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.5.0
[0.4.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.4.0
[0.3.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.3.0
[0.2.1]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.2.1
[0.2.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.2.0
[0.1.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.1.0
