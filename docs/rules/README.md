# HassCheck Rule Index

All 48 rules, grouped by category. Every rule now has a generated docs page.

## HACS structure

| Rule ID | Signal | Docs |
|---|---|---|
| `hacs.custom_components.exists` | Repository has `custom_components/`. | [hacs.custom_components.exists.md](hacs.custom_components.exists.md) |
| `hacs.file.parseable` | Repository has parseable `hacs.json`. | [hacs.file.parseable.md](hacs.file.parseable.md) |
| `brand.icon.exists` | Integration has `custom_components/<domain>/brand/icon.png`. | [brand.icon.exists.md](brand.icon.exists.md) |

## Manifest metadata

| Rule ID | Signal | Docs |
|---|---|---|
| `manifest.exists` | Integration has `manifest.json`. | [manifest.exists.md](manifest.exists.md) |
| `manifest.domain.exists` | Manifest defines `domain`. | [manifest.domain.exists.md](manifest.domain.exists.md) |
| `manifest.domain.matches_directory` | Manifest `domain` matches the integration directory name. | [manifest.domain.matches_directory.md](manifest.domain.matches_directory.md) |
| `manifest.name.exists` | Manifest defines `name`. | [manifest.name.exists.md](manifest.name.exists.md) |
| `manifest.version.exists` | Manifest defines `version`. | [manifest.version.exists.md](manifest.version.exists.md) |
| `manifest.documentation.exists` | Manifest defines `documentation`. | [manifest.documentation.exists.md](manifest.documentation.exists.md) |
| `manifest.issue_tracker.exists` | Manifest defines `issue_tracker`. | [manifest.issue_tracker.exists.md](manifest.issue_tracker.exists.md) |
| `manifest.codeowners.exists` | Manifest defines non-empty `codeowners`. | [manifest.codeowners.exists.md](manifest.codeowners.exists.md) |
| `manifest.iot_class.exists` | Manifest declares `iot_class`. | [manifest.iot_class.exists.md](manifest.iot_class.exists.md) |
| `manifest.iot_class.valid` | Manifest `iot_class` is a recognized value. | [manifest.iot_class.valid.md](manifest.iot_class.valid.md) |
| `manifest.integration_type.exists` | Manifest declares `integration_type`. | [manifest.integration_type.exists.md](manifest.integration_type.exists.md) |
| `manifest.integration_type.valid` | Manifest `integration_type` is a recognized value. | [manifest.integration_type.valid.md](manifest.integration_type.valid.md) |
| `manifest.requirements.is_list` | Manifest `requirements` is a JSON array. | [manifest.requirements.is_list.md](manifest.requirements.is_list.md) |
| `manifest.requirements.entries_well_formed` | Manifest `requirements` entries are valid PEP 508 specifiers. | [manifest.requirements.entries_well_formed.md](manifest.requirements.entries_well_formed.md) |
| `manifest.requirements.no_git_or_url_specs` | Manifest `requirements` contains no git/URL install specs. | [manifest.requirements.no_git_or_url_specs.md](manifest.requirements.no_git_or_url_specs.md) |

## Modern Home Assistant patterns

| Rule ID | Signal | Docs |
|---|---|---|
| `config_flow.file.exists` | Integration has `config_flow.py`. | [config_flow.file.exists.md](config_flow.file.exists.md) |
| `config_flow.manifest_flag_consistent` | `config_flow.py` and manifest `config_flow: true` agree. | [config_flow.manifest_flag_consistent.md](config_flow.manifest_flag_consistent.md) |
| `config_flow.user_step.exists` | `config_flow.py` defines `async_step_user` (AST inspection). | [config_flow.user_step.exists.md](config_flow.user_step.exists.md) |
| `config_flow.reauth_step.exists` | `config_flow.py` defines `async_step_reauth` or `async_step_reauth_confirm` (AST inspection). | [config_flow.reauth_step.exists.md](config_flow.reauth_step.exists.md) |
| `config_flow.reconfigure_step.exists` | `config_flow.py` defines `async_step_reconfigure` (AST inspection). | [config_flow.reconfigure_step.exists.md](config_flow.reconfigure_step.exists.md) |
| `config_flow.unique_id.set` | `config_flow.py` calls `async_set_unique_id` (AST inspection). | [config_flow.unique_id.set.md](config_flow.unique_id.set.md) |
| `config_flow.connection_test` | A discovery-flow step awaits a non-plumbing call (AST heuristic). | [config_flow.connection_test.md](config_flow.connection_test.md) |
| `init.async_setup_entry.defined` | `__init__.py` defines `async_setup_entry` (AST inspection). | [init.async_setup_entry.defined.md](init.async_setup_entry.defined.md) |
| `init.runtime_data.used` | `__init__.py` accesses `entry.runtime_data` (HA 2024.4+ pattern, AST inspection). | [init.runtime_data.used.md](init.runtime_data.used.md) |
| `entity.unique_id.set` | At least one entity platform sets `_attr_unique_id` (AST inspection). | [entity.unique_id.set.md](entity.unique_id.set.md) |
| `entity.has_entity_name.set` | At least one entity platform sets `_attr_has_entity_name = True` (AST inspection). | [entity.has_entity_name.set.md](entity.has_entity_name.set.md) |
| `entity.device_info.set` | At least one entity platform sets `_attr_device_info` or returns `DeviceInfo` (AST inspection). | [entity.device_info.set.md](entity.device_info.set.md) |

## Diagnostics and repairs

| Rule ID | Signal | Docs |
|---|---|---|
| `diagnostics.file.exists` | Integration has `diagnostics.py`. | [diagnostics.file.exists.md](diagnostics.file.exists.md) |
| `diagnostics.redaction.used` | `diagnostics.py` uses `async_redact_data` or a local redaction helper (AST inspection). | [diagnostics.redaction.used.md](diagnostics.redaction.used.md) |
| `repairs.file.exists` | Integration has `repairs.py`. | [repairs.file.exists.md](repairs.file.exists.md) |

## Docs and maintenance

| Rule ID | Signal | Docs |
|---|---|---|
| `docs.readme.exists` | Repository has a README. | [docs.readme.exists.md](docs.readme.exists.md) |
| `docs.installation.exists` | README contains an Installation section (HACS or manual). | [docs.installation.exists.md](docs.installation.exists.md) |
| `docs.configuration.exists` | README contains a Configuration / Setup section. | [docs.configuration.exists.md](docs.configuration.exists.md) |
| `docs.troubleshooting.exists` | README contains a Troubleshooting / FAQ / Support section. | [docs.troubleshooting.exists.md](docs.troubleshooting.exists.md) |
| `docs.removal.exists` | README contains a Removal / Uninstall section. | [docs.removal.exists.md](docs.removal.exists.md) |
| `docs.privacy.exists` | README addresses privacy / data / cloud / local handling. | [docs.privacy.exists.md](docs.privacy.exists.md) |
| `repo.license.exists` | Repository has a license file. | [repo.license.exists.md](repo.license.exists.md) |

## Tests and CI

| Rule ID | Signal | Docs |
|---|---|---|
| `tests.folder.exists` | Repository has `tests/`. | [tests.folder.exists.md](tests.folder.exists.md) |
| `tests.config_flow.detected` | `tests/` contains config flow test coverage (filename, import, or function name). | [tests.config_flow.detected.md](tests.config_flow.detected.md) |
| `tests.setup_entry.detected` | `tests/` references `async_setup_entry` or `async_unload_entry`. | [tests.setup_entry.detected.md](tests.setup_entry.detected.md) |
| `tests.unload.detected` | `tests/` references `async_unload_entry` or unload test functions. | [tests.unload.detected.md](tests.unload.detected.md) |
| `ci.github_actions.exists` | Repository has `.github/workflows/*.yml` or `.yaml`. | [ci.github_actions.exists.md](ci.github_actions.exists.md) |

## Maintenance

| Rule ID | Signal | Docs |
|---|---|---|
| `maintenance.recent_commit.detected` | HEAD commit is within the last 12 months (local git history). | [maintenance.recent_commit.detected.md](maintenance.recent_commit.detected.md) |
| `maintenance.recent_release.detected` | Most recent version tag is within the last 12 months (local git tags). | [maintenance.recent_release.detected.md](maintenance.recent_release.detected.md) |
| `maintenance.changelog.exists` | Repository has a changelog file (`CHANGELOG.md`, `HISTORY.md`, etc.). | [maintenance.changelog.exists.md](maintenance.changelog.exists.md) |
