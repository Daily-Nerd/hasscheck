# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.13.0] — 2026-05-02

### Added
- **`report.provenance` block** in JSON report schema (#130). New optional `Provenance` model carries GitHub Actions context (`source`, `repository`, `commit_sha`, `ref`, `workflow`, `run_id`, `run_attempt`, `actor`, `published_at`, `verified_by`). CLI populates from `GITHUB_*` env vars when running in GitHub Actions; sets `source: "local"` otherwise. `verified_by` is always `null` from the CLI — only the hosted hub sets this after OIDC validation.
- **Schema bump**: `schema_version` `0.3.0` → `0.4.0` (additive per ADR 0009). Reports without a `provenance` key remain valid (field defaults to `null`).
- **`hasscheck publish --dry-run`** (#131). Validates the publish path — runs the check, resolves the endpoint (showing which source won: `--to` flag / env var / `hasscheck.yaml` / default), detects OIDC token presence — without making any network request. Also works with `--withdraw` and `--withdraw-all` to preview what would be deleted.
- **PyPI trusted publishing** (#15). `release.yml` now builds and publishes to PyPI on every `v*.*.*` tag using OIDC trusted publishing (no stored token). `pyproject.toml` classifier bumped `3 - Alpha` → `4 - Beta`. README gains `pip install hasscheck` / `uv tool install hasscheck` install section.
- **`hasscheck badge` marked local preview only** (#67). `docs/architecture/badges.md` gains a trust-level section explaining that committed badge JSON is self-reported; hub-verified badge URLs (v1.0) should replace `raw.githubusercontent.com` embeds once available. CLI docstring updated accordingly.
- **Upgrade Radar framing + ADR 0011** (#132). `idea.md` §1 gains a North star section positioning HassCheck as the upgrade-readiness signal for HA custom integrations. §3 v1.0 ladder entry and §15 Month 9+ goal updated accordingly. New `docs/decisions/0011-upgrade-radar-status-taxonomy.md` defines the five-state hub status model: Fresh / Warnings / Failing / Stale / Unverified, with calculation rules, window rationale, display contract, and CLI behaviour notes.

## [0.12.0] — 2026-05-02

### Added
- **Per-rule settings** in `hasscheck.yaml` (#117). `RuleOverride` gains an optional `settings: dict[str, Any] | None` field so users can tune per-rule behavior without monkey-patching:
  ```yaml
  rules:
    maintenance.recent_commit.detected:
      settings:
        max_age_months: 18
  ```
- **`get_rule_setting(context, rule_id, key, default)`** helper in `src/hasscheck/rules/base.py` for rule check functions to read configured values with default fallback.
- **`ProjectContext.rule_settings: dict[str, dict[str, Any]]`** — populated by `checker.py` from the loaded `HassCheckConfig` and forwarded through `detect_project()`.
- **#109 maintenance rules now read configurable thresholds**:
  - `maintenance.recent_commit.detected` reads `max_age_months` (default `12`)
  - `maintenance.recent_release.detected` reads `max_age_months` (default `12`)
  - `_resolve_max_age()` validates the configured value is `int > 0`; falls back to default on bad input (string, negative, zero, missing, wrong type)
- **Four more README content rules** in `src/hasscheck/rules/docs_readme.py` (#102) — same factory + heading-only heuristic as v0.9 PR #97:
  - `docs.examples.exists` — examples, example, usage, demo
  - `docs.supported_devices.exists` — supported, devices, services, hardware, compatibility, models
  - `docs.limitations.exists` — limitations, caveats, known limitations, restrictions
  - `docs.hacs_instructions.exists` — hacs, custom repository, hacs install
- **`examples/good_integration/README.md`** — extended with four new sections (Examples, Supported Devices, Limitations, HACS Installation) so the positive integration test continues asserting PASS across the full docs rule pack.

### Removed
- **`imports_async_redact` field** from `_DiagnosticsSignals` in `src/hasscheck/rules/diagnostics.py` (#106). The field was captured by the AST walker but never consulted in PASS resolution — design D6 narrowed PASS to "actual call required, import alone is not evidence." Path B from #106 locks the conservative stance permanently and removes the dead carrier. PASS-resolution behavior unchanged.

### Changed
- Bumped `version` and `__version__` to `0.12.0`

### Notes
- `SCHEMA_VERSION` unchanged at `0.3.0` — v0.12 adds a config-file field and removes a private dataclass member; no `Finding` (report) shape changes (additive only per ADR 0009)
- `DEFAULT_RULESET_ID` unchanged at `hasscheck-ha-2026.5` — same ruleset cycle as v0.8 / v0.9 / v0.10 / v0.11 per ADR 0006
- Rule count: 48 → **52** (+4)
- Test count: 737 → **823** (+86 — 25 config + 12 maintenance threshold + 49 README extras)
- Per-rule docs pages: 48 → **52** (4 new auto-generated via `hasscheck docs-render`)
- Backward compat: existing `hasscheck.yaml` files work unchanged; missing `settings` block → all rules use hardcoded defaults

[Compare v0.11.0...v0.12.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.11.0...v0.12.0)

## [0.11.0] — 2026-05-02

### Added
- **Integration test detection rules** in a new `src/hasscheck/rules/tests.py` module — heuristic static inspection (no pytest execution) detecting whether the integration's `tests/` folder covers config flow, setup entry, and unload paths (#108):
  - `tests.config_flow.detected` — filename pattern `^test_config_flow.*\.py$` OR AST imports of `config_flow` OR function names like `test_config_flow_*` / `test_async_step_*`
  - `tests.setup_entry.detected` — AST references to `async_setup_entry` / `async_unload_entry` OR function names like `test_setup_entry_*`
  - `tests.unload.detected` — AST references to `async_unload_entry` OR function names like `test_unload_*` / `test_async_unload*`
- **Maintenance signal rules** in a new `src/hasscheck/rules/maintenance.py` module — local git only, no GitHub API (#109):
  - `maintenance.recent_commit.detected` — `git log -1 --format=%ct` HEAD timestamp; PASS within 12 months, WARN otherwise, NOT_APPLICABLE if no `.git/` or git not on PATH
  - `maintenance.recent_release.detected` — most recent tag timestamp via `git for-each-ref refs/tags`; PASS within 12 months, WARN if older, NOT_APPLICABLE if no tags (unreleased ≠ abandoned)
  - `maintenance.changelog.exists` — file presence at repo root for any of `CHANGELOG.md`, `CHANGELOG`, `HISTORY.md`, `HISTORY`, `RELEASES.md`, `NEWS.md`
- **Auto-generated per-rule docs from `RuleDefinition` metadata** (#104):
  - `src/hasscheck/docs_render.py` — renderer module (`render_page`, `write_page`, `render_all`, `check_drift`)
  - `hasscheck docs-render` Typer subcommand with `--check` mode for CI drift detection
  - `<!-- HANDWRITTEN BELOW THIS LINE -->` marker convention preserves user-written examples below the auto-section
  - 41 new auto-generated pages cover every rule that previously sat in the index with "(no docs page yet)"; the 7 hand-written pages from v0.9 were migrated into the marker convention
  - `tests/test_docs_rules_coverage.py` — parametrized meta-test asserting every registered rule has a `docs/rules/<rule_id>.md`, plus an orphan-page check for rules that were removed
  - `.github/workflows/ci.yml` — drift check step that fails CI if a rule's metadata changed without regenerating docs
- **Demo recording assets** in `docs/` (#105):
  - `docs/demo.sh` — deterministic shell script copying `examples/bad_integration` to `mktemp -d` and running check → explain → scaffold dry-run → scaffold → re-check
  - `docs/recording.md` — instructions for the asciinema rec + agg pipeline, acceptance criteria reminders, README embed snippet
  - README "See it in action" placeholder for `docs/demo.gif` once it lands

### Changed
- Bumped `version` and `__version__` to `0.11.0`
- `docs/rules/README.md` — all 41 `(no docs page yet)` rows replaced with real links; rule count header bumped to 48
- `docs/demo.md` — leading callout linking to `demo.gif` and `recording.md`

### Notes
- `SCHEMA_VERSION` unchanged at `0.3.0` — v0.11 adds no new finding fields (additive only per ADR 0009)
- `DEFAULT_RULESET_ID` unchanged at `hasscheck-ha-2026.5` — same ruleset cycle as v0.8 / v0.9 / v0.10 per ADR 0006
- Rule count: 42 → **48** (+6 — three test detection + three maintenance signal)
- Test count: 606 → **737** (+131 — 33 test-detection + 25 maintenance + 24 docs-renderer + 49 docs-coverage parametrized)
- `_MAX_AGE_MONTHS = 12` for maintenance rules is hardcoded; **#117** tracks the per-rule settings infrastructure that will make it configurable via `hasscheck.yaml`
- Demo `.cast` + `.gif` artifacts intentionally not in this release — they require an interactive PTY to record. Maintainer commits them as a follow-up

[Compare v0.10.0...v0.11.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.10.0...v0.11.0)

## [0.10.0] — 2026-05-01

### Added
- **Manifest requirements sanity rules** in `src/hasscheck/rules/manifest.py` (#100):
  - `manifest.requirements.is_list` (REQUIRED, non-overridable) — FAIL when `requirements` is present but not a JSON array
  - `manifest.requirements.entries_well_formed` (RECOMMENDED, overridable) — PEP 508 parse via `packaging.requirements.Requirement`; FAIL on any unparseable entry; URL/git specs are filtered out before parsing (rule 3 owns that signal)
  - `manifest.requirements.no_git_or_url_specs` (RECOMMENDED, overridable) — WARN when entries use `git+`, `http://`, `https://`, `file://`, or `@ git+` install specs
- **Config flow advanced detection rules** in `src/hasscheck/rules/config_flow.py` (#101):
  - `config_flow.reauth_step.exists` — `async_step_reauth` or `async_step_reauth_confirm` AsyncFunctionDef
  - `config_flow.reconfigure_step.exists` — `async_step_reconfigure` AsyncFunctionDef
  - `config_flow.unique_id.set` — any `Call` to `async_set_unique_id` (Name or Attribute)
  - `config_flow.connection_test` — discovery flow step (`async_step_user`/`zeroconf`/`dhcp`/`bluetooth`/`usb`) awaits a non-plumbing call (heuristic: not `async_show_form` / `async_create_entry` / `async_abort` / `async_set_unique_id` / `_abort_if_unique_id_configured` / any `async_step_*`)
- **Modern HA pattern rules** across two new modules (#107):
  - `src/hasscheck/rules/init_module.py`:
    - `init.async_setup_entry.defined` — `__init__.py` defines `async_setup_entry`
    - `init.runtime_data.used` — `__init__.py` accesses `entry.runtime_data` (HA 2024.4+ pattern)
  - `src/hasscheck/rules/entity.py`:
    - `entity.unique_id.set` — at least one entity platform file sets `_attr_unique_id` (class-level or instance-level)
    - `entity.has_entity_name.set` — at least one entity platform file sets `_attr_has_entity_name = True` (literal True)
    - `entity.device_info.set` — at least one entity platform file sets `_attr_device_info` or returns `DeviceInfo(...)` from a `device_info` method/property
    - Canonical `_HA_PLATFORM_NAMES` frozenset (~40 platform names sourced from HA core's `Platform` enum) drives multi-file iteration
- `hasscheck.ast_utils.has_async_function(tree, name)` — extracted as a public helper from the inline `_has_async_function` previously living in `config_flow.py`. Third extraction after `parse_module` (#93). `config_flow.py`'s local copy delegates to the public version.
- `examples/bad_integration/custom_components/demo_bad/__init__.py` — minimal legacy `setup()` fixture so the bad-integration fixture demonstrates `init.*` WARNs deterministically. The fixture's `manifest.json` gained a `"requirements"` array with one valid + one `git+` entry to demonstrate `manifest.requirements.no_git_or_url_specs` WARN.
- `CONTRIBUTING.md` — issue-first workflow, rule-add checklist, rule philosophy (sourced + conservative + overridable + no-certification language), conventional commits.
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1, fetched canonical from EthicalSource source repo with maintainer contact filled in.
- README "How HassCheck relates to other tools" / "See it in action" / hasscheck.io launch note (#110, #111).
- `idea.md` Section 3 (Product ladder) and Section 15 (Roadmap) refreshed to reflect v0.7→v0.9 reality + v0.10 in-progress + v1.0 hub prerequisites (#111).

### Changed
- Bumped `version` and `__version__` to `0.10.0`
- `packaging>=23.0` added to `[project] dependencies` — was already transitive via `pip` and `setuptools`; made explicit for runtime-surface honesty
- `tests/test_cli.py::test_terminal_applicability_finding_has_config_marker` assertion split — long rule IDs cause Rich to wrap the rule line and `(config)` marker across rendered lines. Behavior under test still verified, just not as a single contiguous string.

### Notes
- `SCHEMA_VERSION` unchanged at `0.3.0` — v0.10 adds no new finding fields (additive only per ADR 0009)
- `DEFAULT_RULESET_ID` unchanged at `hasscheck-ha-2026.5` — same ruleset cycle as v0.8 + v0.9 per ADR 0006
- Rule count: 30 → **42** (+12 — three batches of 3 / 4 / 5)
- Test count: 486 → **606** (+120 across the three rule-expansion batches)
- New rule modules: `src/hasscheck/rules/init_module.py`, `src/hasscheck/rules/entity.py`
- Net new public AST helpers: `parse_module` (already shipped in v0.9), `has_async_function`

[Compare v0.9.0...v0.10.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.9.0...v0.10.0)

## [0.9.0] — 2026-05-01

### Added
- Five README content-detection rules in a new `src/hasscheck/rules/docs_readme.py` module — all RECOMMENDED, overridable, WARN-on-missing; conservative heading-only heuristics with code-fence stripping (#55):
  - `docs.installation.exists` — installation, install, hacs, manual installation, manual install
  - `docs.configuration.exists` — configuration, configure, setup, options
  - `docs.troubleshooting.exists` — troubleshooting, troubleshoot, known issues, known limitations, faq, support, debug
  - `docs.removal.exists` — removal, remove, uninstall, uninstalling
  - `docs.privacy.exists` — privacy, data, telemetry, cloud, local
- `src/hasscheck/ast_utils.py` — public `parse_module(path) -> (ast.Module | None, str | None)`. Single source for AST file parsing previously duplicated inline in `config_flow.py` and `diagnostics.py` (#93)
- `docs/rules/` — new directory containing an index of all 30 rules grouped by category, plus seven hand-written per-rule pages for the highest-leverage rules (manifest.domain.matches_directory, manifest.iot_class.valid, manifest.integration_type.valid, config_flow.user_step.exists, diagnostics.redaction.used, docs.installation.exists, docs.privacy.exists). Auto-generation from `RuleDefinition` metadata deferred to a future release (#58)
- `docs/demo.md` — copy-paste walkthrough using the tracked `examples/bad_integration` fixture: check → explain → scaffold dry-run → re-check loop. Real captured output snippets (#59)
- README "How HassCheck relates to other tools" section — comparison table positioning HassCheck against hassfest, HACS publishing docs, and the HA Integration Quality Scale. Explicit "complementary, not a replacement" framing (#57)
- README "See it in action" section linking to `docs/demo.md`
- README "Documentation" link pointing to `docs/rules/`
- `examples/good_integration/README.md` extended with the five required sections (Installation / Configuration / Troubleshooting / Removal / Privacy) so the new positive integration test passes

### Changed
- Bumped `version` and `__version__` to `0.9.0`
- `_parse_module` removed from `src/hasscheck/rules/config_flow.py` and `src/hasscheck/rules/diagnostics.py`; both now import `parse_module` from the shared `hasscheck.ast_utils`. `assert tree is not None` correlation-narrowing guards preserved at call sites
- Rule count bumped from 25 to 30 (`tests/test_rules_meta.py`). Locked count unchanged (all five new rules are overridable)
- README "Current rule set" extended with five new rows under "Docs and maintenance"

### Notes
- `SCHEMA_VERSION` unchanged at `0.3.0` — v0.9 adds no new finding fields (additive only per ADR 0009)
- `DEFAULT_RULESET_ID` unchanged at `hasscheck-ha-2026.5` — same ruleset cycle as v0.8 per ADR 0006
- Test count: 435 → **486** (+51 across the ast_utils extraction, README content rules, and integration tests)
- Documentation-only PRs (#57 / #58 / #59 bundled in #98) preserve the unofficial / no-certification stance throughout — no "certify" / "approved" / "ready" / "safe" language anywhere

[Compare v0.8.1...v0.9.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.8.1...v0.9.0)

## [0.8.1] — 2026-05-01

### Fixed
- `tests/test_check_version.py` no longer fails pytest collection. Added `pythonpath = ["src", "."]` to `[tool.pytest.ini_options]` and an empty `scripts/__init__.py` so `from scripts.check_version import ...` resolves. The previous `--ignore=tests/test_check_version.py` workaround used during the v0.8.0 SDD cycle is no longer needed (#91)
- Pylance type narrowing on `src/hasscheck/rules/manifest.py:50` and `:155`. `json.loads()` returns `Any`, so explicit `cast(dict[str, Any], payload)` and `cast(list[Any], value)` calls preserve the typed shape across `isinstance` narrowing. No behavior change (#92)

### Changed
- Bumped `version` and `__version__` to `0.8.1`

[Compare v0.8.0...v0.8.1](https://github.com/Daily-Nerd/hasscheck/compare/v0.8.0...v0.8.1)

## [0.8.0] — 2026-05-01

### Added
- Seven new rules covering manifest correctness, config flow, and diagnostics safety:
  - `manifest.domain.matches_directory` (REQUIRED, non-overridable) — catches manifest `domain` vs. `custom_components/<dir>` identity drift (#51)
  - `manifest.iot_class.exists` / `manifest.iot_class.valid` (RECOMMENDED, overridable) — verified against HA dev docs allowed set (#52)
  - `manifest.integration_type.exists` / `manifest.integration_type.valid` (RECOMMENDED, overridable) — verified against HA dev docs allowed set (#52)
  - `config_flow.user_step.exists` (RECOMMENDED, overridable) — AST-walks `config_flow.py` for `async_step_user` AsyncFunctionDef at any depth (#54)
  - `diagnostics.redaction.used` (RECOMMENDED, overridable) — AST detects `async_redact_data` calls or local `^_?redact(_.*)?$` helpers; flags raw `entry.data` / `entry.options` / `dict(entry.data)` returns with strong "likely exposes secrets" wording (#53)
- Inline `_parse_module(path) -> (ast.Module | None, str | None)` 3-state parser pattern in `config_flow.py` and `diagnostics.py` (extract to `ast_utils.py` deferred to v0.9)
- `examples/bad_integration/custom_components/demo_bad/` — tracked negative fixture demonstrating five representative failures (manifest domain mismatch, invalid `iot_class`, missing `integration_type`, missing `async_step_user`, raw `entry.data` diagnostics) (#50)
- `publish.endpoint` block in `hasscheck.yaml` — new fourth precedence tier (CLI flag > env var > config > default) for `hasscheck publish`. `PublishConfig` Pydantic sub-model with `extra="forbid"`
- `--force` flag on `hasscheck publish` — required for non-interactive callers; without it, withdraw branches prompt via `typer.confirm(abort=True)` with report ID + endpoint + irreversibility note
- `--enable-publish` flag on `hasscheck init` — selects sibling workflow template (`github_action_publish.yml.tmpl`) with `id-token: write` permission and `emit-publish: 'true'` step
- `LICENSE` — MIT License at repository root, "Copyright (c) 2026 Daily Nerd"
- `pyproject.toml` PyPI-grade metadata: `license = "MIT"` (SPDX/PEP 639), `authors`, `keywords`, `classifiers`, and `[project.urls]` (Homepage, Repository, Issues, Documentation)
- ADR 0009 — Schema versioning policy: documents `SCHEMA_VERSION` bump triggers, additive-only stance, lockstep with `hasscheck-web`, and distinction from ADR 0006's ruleset versioning

### Changed
- Bumped `version` and `__version__` to `0.8.0`
- `DEFAULT_RULESET_ID` bumped from `hasscheck-ha-2026.4` to `hasscheck-ha-2026.5` (per ADR 0006 — new rules added)
- `resolve_endpoint(cli_value, *, config: HassCheckConfig | None = None)` — keyword-only `config` param; existing call sites unchanged
- `hasscheck publish` CLI handler now loads `hasscheck.yaml` via `discover_config()` before endpoint resolution; malformed YAML surfaces as `ConfigError` rather than opaque `PublishError`
- Diagnostics scaffold template (`src/hasscheck/scaffold/templates/diagnostics.py.tmpl`) and golden updated to pass `diagnostics.redaction.used`
- `cross-reference` header comments added to both `github_action.yml.tmpl` and `github_action_publish.yml.tmpl` to mitigate two-template drift
- README "Current status" block reflects v0.7.0 as latest release and v0.8.0 as in-progress at the time of writing
- README GitHub Action examples bumped from `@v0.6.0` to `@v0.7.0`
- README "Current rule set" tables extended with the seven new rules

### Notes
- **Breaking for non-interactive `hasscheck publish --withdraw` callers**: pipelines must add `--force` to bypass the confirmation prompt (deliberate; `typer.confirm(abort=True)` is the gate)
- `SCHEMA_VERSION` unchanged at `0.3.0` — v0.8 adds no new finding fields (additive only per ADR 0009)
- Test count: ~330 → 430 (+100 across the four rule-depth PRs and the publish-polish PR)

[Compare v0.7.0...v0.8.0](https://github.com/Daily-Nerd/hasscheck/compare/v0.7.0...v0.8.0)

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

[Unreleased]: https://github.com/Daily-Nerd/hasscheck/compare/v0.12.0...HEAD
[0.12.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.12.0
[0.11.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.11.0
[0.10.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.10.0
[0.9.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.9.0
[0.8.1]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.8.1
[0.8.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.8.0
[0.7.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.7.0
[0.6.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.6.0
[0.5.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.5.0
[0.4.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.4.0
[0.3.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.3.0
[0.2.1]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.2.1
[0.2.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.2.0
[0.1.0]: https://github.com/Daily-Nerd/hasscheck/releases/tag/v0.1.0
