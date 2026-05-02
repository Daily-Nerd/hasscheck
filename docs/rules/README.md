# HassCheck Rule Index

All 33 rules, grouped by category. Rules with a dedicated docs page are linked; others show "(no docs page yet)".

## HACS structure

| Rule ID | Signal | Docs |
|---|---|---|
| `hacs.custom_components.exists` | Repository has `custom_components/`. | (no docs page yet) |
| `hacs.file.parseable` | Repository has parseable `hacs.json`. | (no docs page yet) |
| `brand.icon.exists` | Integration has `custom_components/<domain>/brand/icon.png`. | (no docs page yet) |

## Manifest metadata

| Rule ID | Signal | Docs |
|---|---|---|
| `manifest.exists` | Integration has `manifest.json`. | (no docs page yet) |
| `manifest.domain.exists` | Manifest defines `domain`. | (no docs page yet) |
| `manifest.domain.matches_directory` | Manifest `domain` matches the integration directory name. | [manifest.domain.matches_directory.md](manifest.domain.matches_directory.md) |
| `manifest.name.exists` | Manifest defines `name`. | (no docs page yet) |
| `manifest.version.exists` | Manifest defines `version`. | (no docs page yet) |
| `manifest.documentation.exists` | Manifest defines `documentation`. | (no docs page yet) |
| `manifest.issue_tracker.exists` | Manifest defines `issue_tracker`. | (no docs page yet) |
| `manifest.codeowners.exists` | Manifest defines non-empty `codeowners`. | (no docs page yet) |
| `manifest.iot_class.exists` | Manifest declares `iot_class`. | (no docs page yet) |
| `manifest.iot_class.valid` | Manifest `iot_class` is a recognized value. | [manifest.iot_class.valid.md](manifest.iot_class.valid.md) |
| `manifest.integration_type.exists` | Manifest declares `integration_type`. | (no docs page yet) |
| `manifest.integration_type.valid` | Manifest `integration_type` is a recognized value. | [manifest.integration_type.valid.md](manifest.integration_type.valid.md) |
| `manifest.requirements.is_list` | Manifest `requirements` is a JSON array. | (no docs page yet) |
| `manifest.requirements.entries_well_formed` | Manifest `requirements` entries are valid PEP 508 specifiers. | (no docs page yet) |
| `manifest.requirements.no_git_or_url_specs` | Manifest `requirements` contains no git/URL install specs. | (no docs page yet) |

## Modern Home Assistant patterns

| Rule ID | Signal | Docs |
|---|---|---|
| `config_flow.file.exists` | Integration has `config_flow.py`. | (no docs page yet) |
| `config_flow.manifest_flag_consistent` | `config_flow.py` and manifest `config_flow: true` agree. | (no docs page yet) |
| `config_flow.user_step.exists` | `config_flow.py` defines `async_step_user` (AST inspection). | [config_flow.user_step.exists.md](config_flow.user_step.exists.md) |

## Diagnostics and repairs

| Rule ID | Signal | Docs |
|---|---|---|
| `diagnostics.file.exists` | Integration has `diagnostics.py`. | (no docs page yet) |
| `diagnostics.redaction.used` | `diagnostics.py` uses `async_redact_data` or a local redaction helper (AST inspection). | [diagnostics.redaction.used.md](diagnostics.redaction.used.md) |
| `repairs.file.exists` | Integration has `repairs.py`. | (no docs page yet) |

## Docs and maintenance

| Rule ID | Signal | Docs |
|---|---|---|
| `docs.readme.exists` | Repository has a README. | (no docs page yet) |
| `docs.installation.exists` | README contains an Installation section (HACS or manual). | [docs.installation.exists.md](docs.installation.exists.md) |
| `docs.configuration.exists` | README contains a Configuration / Setup section. | (no docs page yet) |
| `docs.troubleshooting.exists` | README contains a Troubleshooting / FAQ / Support section. | (no docs page yet) |
| `docs.removal.exists` | README contains a Removal / Uninstall section. | (no docs page yet) |
| `docs.privacy.exists` | README addresses privacy / data / cloud / local handling. | [docs.privacy.exists.md](docs.privacy.exists.md) |
| `repo.license.exists` | Repository has a license file. | (no docs page yet) |

## Tests and CI

| Rule ID | Signal | Docs |
|---|---|---|
| `tests.folder.exists` | Repository has `tests/`. | (no docs page yet) |
| `ci.github_actions.exists` | Repository has `.github/workflows/*.yml` or `.yaml`. | (no docs page yet) |
