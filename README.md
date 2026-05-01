# HassCheck

HassCheck is an **unofficial** CLI for Home Assistant community integration maintainers.

It checks custom integration repositories for sourced HA/HACS quality signals and produces explainable, actionable reports.

```text
Security Review: Not performed
Official HA Tier: Not assigned
HACS Acceptance: Not guaranteed
```

HassCheck is not affiliated with Home Assistant, HACS, Nabu Casa, or the Open Home Foundation. It does **not** certify integrations, prove that an integration is safe, or guarantee HACS acceptance.

## What HassCheck does

HassCheck turns scattered Home Assistant and HACS expectations into local checks that are:

- **Sourced** — every finding carries a source URL and checked date.
- **Explainable** — each rule has a stable ID, version, title, reason, and fix suggestion.
- **Actionable** — output points maintainers toward concrete next fixes.
- **Machine-readable** — JSON output is the stable contract for future GitHub Actions, badges, hosted reports, and tooling.

HassCheck starts as a local CLI. Public badges, hosted reports, and any future hub should be opt-in only.

## Current status

HassCheck is at the v0.1.0 walking-skeleton stage.

It already has:

- Typer CLI
- Rich terminal output
- Pydantic JSON report schema
- Rule IDs and rule versions
- Source links and source timestamps
- Applicability-aware statuses
- Example good/partial/bad integration fixtures
- Pytest coverage for the current rule set

## Install for local development

This repository uses [`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

Run the CLI without installing globally:

```bash
.venv/bin/python -m hasscheck --help
```

## Commands

### Check a repository

```bash
.venv/bin/python -m hasscheck check --path .
```

### Emit JSON

```bash
.venv/bin/python -m hasscheck check --path . --json
```

### Print the JSON schema

```bash
.venv/bin/python -m hasscheck schema
```

### Explain a rule

```bash
.venv/bin/python -m hasscheck explain manifest.domain.exists
```

## Finding statuses

HassCheck findings use explicit statuses instead of a single global certification score.

| Status | Meaning |
| --- | --- |
| `pass` | The signal was found. |
| `warn` | The signal is missing or incomplete, but should not block every project. |
| `fail` | The repository has an internally inconsistent or required metadata problem. |
| `not_applicable` | The rule does not apply yet or cannot be evaluated from current context. |
| `manual_review` | Human judgment is needed. |

## Example terminal output

```text
HassCheck Summary

Diagnostics/Repairs: 2 / 2
Docs/Support: 1 / 1
HACS Structure: 3 / 3
Maintenance Signals: 1 / 1
Manifest Metadata: 7 / 7
Modern HA Patterns: 2 / 2
Tests/CI: 2 / 2

Overall: Informational only
Security Review: Not performed
Official HA Tier: Not assigned
HACS Acceptance: Not guaranteed
```

The exact category order may change as rules evolve. The JSON schema is the durable contract.

## Current rule set

### HACS structure

| Rule ID | Signal |
| --- | --- |
| `hacs.custom_components.exists` | Repository has `custom_components/`. |
| `hacs.file.parseable` | Repository has parseable `hacs.json`. |
| `brand.icon.exists` | Integration has `custom_components/<domain>/brand/icon.png`. |

### Manifest metadata

| Rule ID | Signal |
| --- | --- |
| `manifest.exists` | Integration has `manifest.json`. |
| `manifest.domain.exists` | Manifest defines `domain`. |
| `manifest.name.exists` | Manifest defines `name`. |
| `manifest.version.exists` | Manifest defines `version`. |
| `manifest.documentation.exists` | Manifest defines `documentation`. |
| `manifest.issue_tracker.exists` | Manifest defines `issue_tracker`. |
| `manifest.codeowners.exists` | Manifest defines non-empty `codeowners`. |

### Modern Home Assistant patterns

| Rule ID | Signal |
| --- | --- |
| `config_flow.file.exists` | Integration has `config_flow.py`. |
| `config_flow.manifest_flag_consistent` | `config_flow.py` and manifest `config_flow: true` agree. |

### Diagnostics and repairs

| Rule ID | Signal |
| --- | --- |
| `diagnostics.file.exists` | Integration has `diagnostics.py`. |
| `repairs.file.exists` | Integration has `repairs.py`. |

### Docs and maintenance

| Rule ID | Signal |
| --- | --- |
| `docs.readme.exists` | Repository has a README. |
| `repo.license.exists` | Repository has a license file. |

### Tests and CI

| Rule ID | Signal |
| --- | --- |
| `tests.folder.exists` | Repository has `tests/`. |
| `ci.github_actions.exists` | Repository has `.github/workflows/*.yml` or `.yaml`. |

## JSON report contract

JSON output includes:

- `schema_version`
- tool metadata
- project metadata
- ruleset metadata
- category summaries
- findings with rule IDs, rule versions, statuses, applicability, source URLs, and fix suggestions

Example:

```bash
.venv/bin/python -m hasscheck check --path examples/good_integration --json
```

Use `hasscheck schema` to inspect the full report schema.

## Development

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run HassCheck against the good fixture:

```bash
.venv/bin/python -m hasscheck check --path examples/good_integration
```

Run HassCheck against the current repository:

```bash
.venv/bin/python -m hasscheck check --path .
```

## Release checklist for v0.1.0

Before tagging v0.1.0:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m hasscheck check --path examples/good_integration
.venv/bin/python -m hasscheck check --path examples/good_integration --json
.venv/bin/python -m hasscheck schema
.venv/bin/python -m hasscheck explain manifest.domain.exists
```

Then tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Non-goals for v0.1.0

HassCheck v0.1.0 does not attempt:

- Security certification
- Official Home Assistant quality tier assignment
- HACS acceptance guarantees
- Runtime testing against physical devices
- Full semantic correctness checks
- Public crawling or ranking of random repositories
- Automatic PRs to third-party repos

## Philosophy

HassCheck should say:

```text
Automated checks found these quality signals.
```

Not:

```text
This integration is certified, safe, approved, or officially ready.
```
